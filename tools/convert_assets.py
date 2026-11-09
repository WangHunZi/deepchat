"""Prepare role GIFs and reuse Xiaozhi's mmap resource packer."""

import base64
import hashlib
import importlib.util
import io
import json
import re

import collect_assets
from PIL import Image, ImageSequence


def digest(data):
    return hashlib.sha256(data).hexdigest()


def upstream_packer(repo):
    path = repo / "third_party/xiaozhi-esp32/scripts/build_default_assets.py"
    spec = importlib.util.spec_from_file_location("xiaozhi_asset_packer", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_config(path):
    config = json.loads(path.read_text(encoding="utf-8"))
    if config["canvas"] != [240, 240] or len(config["content_box"]) != 2:
        raise ValueError("This profile requires a 240x240 canvas and two content dimensions")
    if any(type(value) is not int or not 1 <= value <= 240 for value in config["content_box"]):
        raise ValueError("Content dimensions must be integers within 1..240")
    if type(config["fps_cap"]) is not int or config["fps_cap"] not in (5, 10):
        raise ValueError("Supported frame sampling caps: 5 or 10 fps")
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", config["background"]):
        raise ValueError("Background must be an RGB hex color")
    if type(config["budget_bytes"]) is not int or not 1 <= config["budget_bytes"] <= 8388608:
        raise ValueError("Resource budget must fit the reference board's 8 MiB assets partition")
    if not config["clips"] or len(config["clips"]) > 16:
        raise ValueError("Expected 1..16 clips")
    if config["sprite_grid"] != [8, 11]:
        raise ValueError("This profile requires the source 8x11 sprite grid")
    for name, clip in config["clips"].items():
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,15}", name) or type(clip["loop"]) is not bool:
            raise ValueError("Invalid clip name or loop setting")
        if type(clip["sprite_row"]) is not int or not 0 <= clip["sprite_row"] < 11:
            raise ValueError("Sprite row must be within 0..10")
        if not clip["sprite_columns"] or any(type(n) is not int or not 0 <= n < 8 for n in clip["sprite_columns"]):
            raise ValueError("Sprite columns must be within 0..7")
    actions = config["actions"]
    if {a["id"] for a in actions} != {"idle", "listen", "think", "speak", "happy", "confused"} or len(actions) != 6:
        raise ValueError("Exactly six distinct product actions are required")
    emotions = set()
    for action in actions:
        if action["clip"] not in config["clips"] or not re.fullmatch(r"[a-z][a-z0-9-]{0,20}", action["emotion"]):
            raise ValueError("Invalid clip reference or upstream emotion name")
        if action["emotion"] in emotions:
            raise ValueError("Duplicate upstream emotion mapping")
        emotions.add(action["emotion"])
    return config


def read_frames(path):
    with Image.open(path) as source:
        if source.format != "GIF" or max(source.size) > 1024 or source.n_frames > 240:
            raise ValueError("Expected a GIF no larger than 1024x1024 and 240 frames")
        frames, durations = [], []
        for frame in ImageSequence.Iterator(source):
            duration = frame.info.get("duration", 0)
            if not 10 <= duration <= 60000:
                raise ValueError("Every source frame needs a duration of 10..60000 ms")
            frames.append(frame.convert("RGBA"))
            durations.append(duration)
        if sum(durations) > 60000:
            raise ValueError("Source animation exceeds 60 seconds")
    return frames, durations


def sample_frames(frames, durations, fps):
    step = 1000 // fps
    total = sum(durations)
    index, end = 0, durations[0]
    sampled = []
    for position in range(0, total, step):
        while position >= end:
            index += 1
            end += durations[index]
        sampled.append(frames[index])
    return sampled, step


def normalize_frames(clips, config):
    bounds = None
    for frames, _ in clips.values():
        for frame in frames:
            box = frame.getchannel("A").getbbox()
            if box:
                bounds = (
                    box
                    if bounds is None
                    else (
                        min(bounds[0], box[0]),
                        min(bounds[1], box[1]),
                        max(bounds[2], box[2]),
                        max(bounds[3], box[3]),
                    )
                )
    if bounds is None:
        raise ValueError("All source frames are transparent")
    source_size = (bounds[2] - bounds[0], bounds[3] - bounds[1])
    scale = min(config["content_box"][0] / source_size[0], config["content_box"][1] / source_size[1])
    target = (max(1, round(source_size[0] * scale)), max(1, round(source_size[1] * scale)))
    offset = ((240 - target[0]) // 2, (240 - target[1]) // 2)
    converted = {}
    for name, (frames, durations) in clips.items():
        normalized = []
        for frame in frames:
            canvas = Image.new("RGBA", (240, 240), config["background"])
            image = frame.crop(bounds).resize(target, Image.Resampling.LANCZOS)
            canvas.alpha_composite(image, offset)
            normalized.append(canvas.convert("RGB"))
        converted[name] = (normalized, durations)
    return converted, {"source_bounds": bounds, "target_size": target, "offset": offset}


def encode_gifs(clips, config):
    all_frames = [frame for frames, _ in clips.values() for frame in frames]
    strip = Image.new("RGB", (240, 240 * len(all_frames)))
    for index, frame in enumerate(all_frames):
        strip.paste(frame, (0, index * 240))
    palette = strip.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    colors = palette.getpalette()
    for index, value in enumerate(colors):
        bits = 6 if index % 3 == 1 else 5
        channel = value >> (8 - bits)
        colors[index] = (channel << (8 - bits)) | (channel >> (2 * bits - 8))
    palette.putpalette(colors)
    encoded = {}
    for name, (frames, durations) in clips.items():
        sampled, step = sample_frames(frames, durations, config["fps_cap"])
        indexed = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in sampled]
        options = {"loop": 0} if config["clips"][name]["loop"] else {}
        output = io.BytesIO()
        indexed[0].save(
            output,
            format="GIF",
            save_all=True,
            append_images=indexed[1:],
            duration=step,
            optimize=False,
            disposal=1,
            **options,
        )
        encoded[name] = output.getvalue()
    return encoded


def preview_clip(data, loop):
    frames, durations, hashes = [], [], []
    with Image.open(io.BytesIO(data)) as image:
        for frame in ImageSequence.Iterator(image):
            rgb = frame.convert("RGB")
            png = io.BytesIO()
            rgb.save(png, format="PNG")
            frames.append("data:image/png;base64," + base64.b64encode(png.getvalue()).decode())
            hashes.append(digest(rgb.tobytes()))
            durations.append(frame.info["duration"])
    return {
        "frames": frames,
        "frame_sha256": hashes,
        "durations_ms": durations,
        "loop": loop,
        "duration_ms": sum(durations),
        "gif_bytes": len(data),
        "gif": "data:image/gif;base64," + base64.b64encode(data).decode(),
    }


def pack_role(base, encoded, config, packer):
    files = packer.read_assets_entries(base)
    index = json.loads(files["index.json"][0])
    if not isinstance(index, dict) or index.get("version") != 1:
        raise ValueError("Expected upstream version-1 base assets")
    previous = index.get("emoji_collection", [])
    if not isinstance(previous, list):
        raise ValueError("Invalid base emoji collection")
    for entry in previous:
        if not isinstance(entry, dict) or not isinstance(entry.get("file"), str):
            raise ValueError("Invalid base emoji entry")
        files.pop(entry["file"], None)
    for name, data in encoded.items():
        files[f"dc-{name}.gif"] = (data, 240, 240)
    index["emoji_collection"] = [
        {"name": action["emotion"], "file": f"dc-{action['clip']}.gif"} for action in config["actions"]
    ]
    files["index.json"] = (json.dumps(index, ensure_ascii=False).encode(), 0, 0)
    data = packer.pack_assets_entries(files)
    if len(data) > config["budget_bytes"]:
        raise ValueError(f"Packed resources exceed budget: {len(data)} > {config['budget_bytes']} bytes")
    return data


def build_bundle(config_path, local, catalog_path, base, output, repo):
    config = read_config(config_path)
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    pack = catalog["packs"][config["source_pack"]]
    source_root = (local / config["source_pack"]).resolve()
    locked = {entry["path"]: entry for entry in pack["files"]}
    clips, inputs = {}, {}

    def source_bytes(file):
        path = (source_root / file).resolve()
        if not path.is_relative_to(source_root) or file not in locked:
            raise ValueError("Clip path must be inside the source pack and recorded in its source lock")
        data = path.read_bytes()
        collect_assets.verify(data, locked[file])
        inputs[file] = digest(data)
        return data

    with Image.open(io.BytesIO(source_bytes(config["sprite_file"]))) as source:
        if source.format != "WEBP" or source.width % 8 or source.height % 11 or max(source.size) > 4096:
            raise ValueError("Expected a WebP canvas divisible into the locked 8x11 grid")
        sprite = source.convert("RGBA")
    width, height = sprite.width // 8, sprite.height // 11
    for name, description in config["clips"].items():
        _, durations = read_frames(io.BytesIO(source_bytes(description["file"])))
        columns = description["sprite_columns"]
        if len(columns) != len(durations):
            raise ValueError("Sprite mapping and timing GIF frame counts differ")
        row = description["sprite_row"]
        frames = [
            sprite.crop((column * width, row * height, (column + 1) * width, (row + 1) * height)) for column in columns
        ]
        clips[name] = (frames, durations)
    source_dimensions = {frame.size for frames, _ in clips.values() for frame in frames}
    if len(source_dimensions) != 1:
        raise ValueError("Clips must share one source canvas for a stable common anchor")
    normalized, geometry = normalize_frames(clips, config)
    encoded = encode_gifs(normalized, config)
    packed = pack_role(base, encoded, config, upstream_packer(repo))
    previews = {name: preview_clip(data, config["clips"][name]["loop"]) for name, data in encoded.items()}
    report = {
        "name": config["name"],
        "canvas": config["canvas"],
        "background": config["background"],
        "fps_cap": config["fps_cap"],
        "geometry": geometry,
        "source_revision": pack["revision"],
        "source_sha256": inputs,
        "catalog_sha256": digest(catalog_path.read_bytes()),
        "config_sha256": digest(config_path.read_bytes()),
        "base_sha256": digest(base.read_bytes()),
        "upstream_revision": json.loads((repo / "tools/xiaozhi-lock.json").read_text())["revision"],
        "base_path": str(base.resolve().relative_to(repo.resolve())),
        "packed_bytes": len(packed),
        "budget_bytes": config["budget_bytes"],
        "decoder_buffer_estimate_bytes": 240 * 240 * 5,
        "raw_rgb565_frame_bytes": 240 * 240 * 2,
        "actions": config["actions"],
        "clips": previews,
    }
    outputs = {"assets.bin": packed, **{f"dc-{name}.gif": data for name, data in encoded.items()}}
    template = (repo / "tools/preview/index.html").read_text(encoding="utf-8")
    payload = json.dumps(report, ensure_ascii=False).replace("<", "\\u003c")
    outputs["index.html"] = template.replace("__PET_DATA__", payload).encode()
    report["files"] = {name: digest(data) for name, data in outputs.items()}
    report["template_sha256"] = digest(template.encode())
    output.mkdir(parents=True, exist_ok=True)
    for name, data in outputs.items():
        (output / name).write_bytes(data)
    (output / "preview.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Packed {len(encoded)} GIFs: {len(packed)} / {config['budget_bytes']} bytes; preview {output / 'index.html'}"
    )
    return report


def check_bundle(output, repo):
    report = json.loads((output / "preview.json").read_text(encoding="utf-8"))
    for name, expected in report["files"].items():
        path = (output / name).resolve()
        if not path.is_relative_to(output.resolve()) or digest(path.read_bytes()) != expected:
            raise ValueError(f"Converted output differs: {name}")
    packed = upstream_packer(repo).read_assets_entries(output / "assets.bin")
    index = json.loads(packed["index.json"][0])
    expected_mapping = [{"name": action["emotion"], "file": f"dc-{action['clip']}.gif"} for action in report["actions"]]
    if index.get("emoji_collection") != expected_mapping:
        raise ValueError("Packed emotion mapping differs from preview")
    for name, clip in report["clips"].items():
        gif = packed[f"dc-{name}.gif"]
        if gif[1:] != (240, 240):
            raise ValueError(f"Packed image dimensions differ: {name}")
        decoded = preview_clip(gif[0], clip["loop"])
        if decoded != clip:
            raise ValueError(f"Preview is not decoded from the packaged GIF: {name}")
        with Image.open(io.BytesIO(gif[0])) as image:
            if image.size != (240, 240) or (image.info.get("loop") == 0) != clip["loop"]:
                raise ValueError(f"GIF canvas or loop semantics differ: {name}")
    config = repo / "assets/pet/deepseek.json"
    if report["config_sha256"] != digest(config.read_bytes()):
        raise ValueError("Conversion config changed; rebuild the bundle")
    if report["actions"] != json.loads(config.read_text())["actions"]:
        raise ValueError("Preview action mapping differs from conversion config")
    if report["catalog_sha256"] != digest((repo / "assets/sources.json").read_bytes()):
        raise ValueError("Source catalog changed; rebuild the bundle")
    if report["template_sha256"] != digest((repo / "tools/preview/index.html").read_bytes()):
        raise ValueError("Preview template changed; rebuild the bundle")
    base = (repo / report["base_path"]).resolve()
    if not base.is_relative_to(repo.resolve()) or report["base_sha256"] != digest(base.read_bytes()):
        raise ValueError("Base assets changed; rebuild the bundle")
    source_root = repo / "assets/local" / json.loads(config.read_text())["source_pack"]
    for name, expected in report["source_sha256"].items():
        path = (source_root / name).resolve()
        if not path.is_relative_to(source_root.resolve()) or digest(path.read_bytes()) != expected:
            raise ValueError(f"Source changed: {name}")
    if report["upstream_revision"] != json.loads((repo / "tools/xiaozhi-lock.json").read_text())["revision"]:
        raise ValueError("Upstream packer changed; rebuild the bundle")
