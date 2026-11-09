"""Asset conversion, upstream resource and decoder contracts using original fixtures."""

import base64
import copy
import hashlib
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import convert_assets as pipeline
from PIL import Image, ImageChops, ImageDraw, ImageSequence

ROOT = Path(__file__).resolve().parents[2]


class AssetPipelineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        directory = ROOT / "build/asset-tests/decoder"
        directory.mkdir(parents=True, exist_ok=True)
        source = ROOT / "third_party/xiaozhi-esp32/main/display/lvgl_display/gif"
        shim = ROOT / "tests/assets/decoder"
        flags = [
            "-std=c11",
            "-DLV_USE_DRAW_SW_ASM=0",
            "-DLV_DRAW_SW_ASM_HELIUM=1",
            "-DLV_GIF_CACHE_DECODE_DATA=0",
            "-I",
            str(shim),
            "-I",
            str(source),
        ]
        subprocess.run(
            [
                "cc",
                *flags,
                "-Wall",
                "-Wextra",
                "-Wpedantic",
                "-Werror",
                "-c",
                shim / "DCGifDecode.c",
                "-o",
                directory / "adapter.o",
            ],
            check=True,
        )
        subprocess.run(["cc", *flags, "-c", source / "gifdec.c", "-o", directory / "gifdec.o"], check=True)
        cls.decoder = directory / "DCGifDecode"
        subprocess.run(["cc", directory / "adapter.o", directory / "gifdec.o", "-o", cls.decoder], check=True)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "build")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.config_path = self.repo / "assets/pet/deepseek.json"
        self.config_path.parent.mkdir(parents=True)
        self.config = json.loads((ROOT / "assets/pet/deepseek.json").read_text())
        for clip in self.config["clips"].values():
            clip["sprite_columns"] = [0, 1, 2]
        self.config_path.write_text(json.dumps(self.config))
        self.local = self.repo / "assets/local/codex-pet"
        self.local.mkdir(parents=True)
        entries = []
        frames = []
        for index in range(3):
            frame = Image.new("RGBA", (24, 32))
            draw = ImageDraw.Draw(frame)
            draw.rectangle((5 + index, 4, 16 + index, 27), fill=(20 + index * 50, 80, 200, 255))
            frames.append(frame)
        for clip in self.config["clips"].values():
            path = self.local / clip["file"]
            path.parent.mkdir(parents=True, exist_ok=True)
            frames[0].save(
                path,
                format="GIF",
                save_all=True,
                append_images=frames[1:],
                duration=[110, 220, 130],
                loop=0,
                disposal=2,
            )
            raw = path.read_bytes()
            entries.append({"path": clip["file"], "size_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
        sprite = Image.new("RGBA", (24 * 8, 32 * 11))
        for clip in self.config["clips"].values():
            for number, frame in enumerate(frames):
                sprite.paste(frame, (number * 24, clip["sprite_row"] * 32))
        sprite_path = self.local / "spritesheet.webp"
        sprite.save(sprite_path, lossless=True)
        raw = sprite_path.read_bytes()
        entries.append({"path": "spritesheet.webp", "size_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
        self.catalog = self.repo / "assets/sources.json"
        self.catalog.write_text(json.dumps({"packs": {"codex-pet": {"revision": "fixture", "files": entries}}}))
        for file in [
            "tools/preview/index.html",
            "tools/xiaozhi-lock.json",
            "third_party/xiaozhi-esp32/scripts/build_default_assets.py",
        ]:
            path = self.repo / file
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / file, path)
        self.packer = pipeline.upstream_packer(self.repo)
        self.base = self.repo / "base.bin"
        index = {"version": 1, "text_font": "font.bin", "emoji_collection": [{"name": "neutral", "file": "old.gif"}]}
        self.base.write_bytes(
            self.packer.pack_assets_entries(
                {
                    "index.json": (json.dumps(index).encode(), 0, 0),
                    "font.bin": (b"preserved font fixture", 0, 0),
                    "old.gif": ((self.local / "previews/idle.gif").read_bytes(), 24, 32),
                }
            )
        )
        self.output = self.repo / "output"

    def build(self):
        return pipeline.build_bundle(
            self.config_path, self.local.parent, self.catalog, self.base, self.output, self.repo
        )

    def test_packed_gifs_preview_pixels_timings_and_font_are_shared(self):
        report = self.build()
        pipeline.check_bundle(self.output, self.repo)
        packed = self.packer.read_assets_entries(self.output / "assets.bin")
        self.assertEqual(packed["font.bin"][0], b"preserved font fixture")
        self.assertNotIn("old.gif", packed)
        index = json.loads(packed["index.json"][0])
        self.assertEqual(len(index["emoji_collection"]), 6)
        self.assertEqual(report["clips"]["idle"]["duration_ms"], 500)
        for name, clip in report["clips"].items():
            self.assertEqual((self.output / f"dc-{name}.gif").read_bytes(), packed[f"dc-{name}.gif"][0])
            self.assertTrue(all(duration >= 100 for duration in clip["durations_ms"]))
            with Image.open(io.BytesIO(packed[f"dc-{name}.gif"][0])) as gif:
                self.assertEqual(gif.size, (240, 240))
                self.assertEqual(gif.info.get("loop") == 0, clip["loop"])
                for number, frame in enumerate(ImageSequence.Iterator(gif)):
                    png = Image.open(io.BytesIO(base64.b64decode(clip["frames"][number].split(",", 1)[1])))
                    self.assertIsNone(ImageChops.difference(png.convert("RGB"), frame.convert("RGB")).getbbox())

    def test_original_device_decoder_matches_all_generated_pixels_and_durations(self):
        report = self.build()
        for name, clip in report["clips"].items():
            destination = self.repo / f"decoded-{name}"
            destination.mkdir()
            result = subprocess.run(
                [self.decoder, self.output / f"dc-{name}.gif", destination, str(len(clip["frames"]))],
                check=True,
                text=True,
                capture_output=True,
            )
            self.assertEqual(json.loads(result.stdout)["width"], 240)
            self.assertEqual(
                [int(value) for value in (destination / "durations.txt").read_text().split()], clip["durations_ms"]
            )
            bgra = (destination / "frames.bgra").read_bytes()
            expected = bytearray()
            for frame in clip["frames"]:
                with Image.open(io.BytesIO(base64.b64decode(frame.split(",", 1)[1]))) as image:
                    expected.extend(image.convert("RGBA").tobytes("raw", "BGRA"))
            self.assertEqual(bgra, expected)

    def test_changed_input_is_rejected_before_outputs_are_written(self):
        (self.local / "previews/idle.gif").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "does not match"):
            self.build()
        self.assertFalse(self.output.exists())

    def test_timing_gif_colors_do_not_contaminate_clean_sprite_pixels(self):
        path = self.local / "previews/idle.gif"
        Image.new("RGB", (24, 32), (0, 255, 0)).save(path, format="GIF", duration=460)
        self.config["clips"]["idle"]["sprite_columns"] = [0]
        self.config_path.write_text(json.dumps(self.config))
        catalog = json.loads(self.catalog.read_text())
        entry = next(e for e in catalog["packs"]["codex-pet"]["files"] if e["path"] == "previews/idle.gif")
        raw = path.read_bytes()
        entry.update(size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        self.catalog.write_text(json.dumps(catalog))
        report = self.build()
        self.assertEqual(report["clips"]["idle"]["duration_ms"], 500)
        with Image.open(self.output / "dc-idle.gif") as gif:
            green = sum(g > r * 1.25 and g > b * 1.25 and g > 90 for r, g, b in gif.convert("RGB").get_flattened_data())
        self.assertEqual(green, 0)

    def test_clip_cannot_escape_source_directory(self):
        self.config["clips"]["idle"]["file"] = "../outside.gif"
        self.config_path.write_text(json.dumps(self.config))
        with self.assertRaisesRegex(ValueError, "inside the source pack"):
            self.build()

    def test_budget_rejects_pack_without_overwriting_existing_output(self):
        self.config["budget_bytes"] = 1
        self.config_path.write_text(json.dumps(self.config))
        self.output.mkdir()
        (self.output / "assets.bin").write_bytes(b"previous")
        with self.assertRaisesRegex(ValueError, "exceed budget"):
            self.build()
        self.assertEqual((self.output / "assets.bin").read_bytes(), b"previous")

    def test_unknown_action_reference_is_rejected(self):
        self.config["actions"][0]["clip"] = "missing"
        self.config_path.write_text(json.dumps(self.config))
        with self.assertRaisesRegex(ValueError, "clip reference"):
            self.build()

    def test_output_corruption_is_reported(self):
        self.build()
        (self.output / "dc-idle.gif").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "Converted output differs"):
            pipeline.check_bundle(self.output, self.repo)

    def test_changed_config_base_or_template_is_reported(self):
        for file, message in [
            (self.config_path, "config changed"),
            (self.base, "Base assets changed"),
            (self.repo / "tools/preview/index.html", "template changed"),
        ]:
            with self.subTest(file=file):
                original = file.read_bytes()
                self.build()
                file.write_bytes(original + b" ")
                with self.assertRaisesRegex(ValueError, message):
                    pipeline.check_bundle(self.output, self.repo)
                file.write_bytes(original)

    def test_animation_normalization_uses_one_anchor_for_all_frames(self):
        frames = []
        for offset in [0, 5]:
            image = Image.new("RGBA", (30, 30))
            draw = ImageDraw.Draw(image)
            draw.rectangle((2, 2, 5, 5), fill=(255, 0, 0, 255))
            draw.rectangle((10 + offset, 10, 15 + offset, 20), fill=(0, 0, 255, 255))
            frames.append(image)
        normalized, _ = pipeline.normalize_frames({"idle": (frames, [100, 100])}, self.config)
        images = normalized["idle"][0]
        self.assertIsNone(
            ImageChops.difference(images[0].crop((0, 0, 80, 80)), images[1].crop((0, 0, 80, 80))).getbbox()
        )
        self.assertIsNotNone(ImageChops.difference(images[0], images[1]).getbbox())

    def test_rebuilding_same_inputs_is_deterministic(self):
        first = copy.deepcopy(self.build()["files"])
        self.assertEqual(first, self.build()["files"])


if __name__ == "__main__":
    unittest.main()
