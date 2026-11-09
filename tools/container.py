"""Docker transport for the shared development entry; no host SDK is required."""

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INPUTS = (
    "docker/Dockerfile",
    ".dockerignore",
    "tools/native.py",
    "tools/sdk-lock.json",
    "tools/requirements-host.txt",
    "tools/requirements-idf.txt",
    "tools/idf-constraints.txt",
)
PIN = REPO / "config/local/container-image.json"


def run(command, **kwargs):
    return subprocess.run([str(item) for item in command], cwd=REPO, check=True, **kwargs)


def settings():
    value = json.loads((REPO / "tools/container-lock.json").read_text())
    if not isinstance(value, dict):
        raise ValueError("Container lock must be a JSON object")
    if value["platform"] != "linux/amd64":
        raise ValueError("Only the validated linux/amd64 development image is supported")
    require_digest(value["base_image"])
    if value["image"] is not None:
        require_digest(value["image"])
    return value


def require_digest(reference):
    if not isinstance(reference, str) or not re.fullmatch(r"[^\s@]+@sha256:[0-9a-f]{64}", reference):
        raise ValueError("Image references must include an immutable @sha256 digest")


def recipe():
    digest = hashlib.sha256(settings()["base_image"].encode())
    for name in INPUTS:
        digest.update(name.encode() + b"\0" + (REPO / name).read_bytes() + b"\0")
    return digest.hexdigest()


def ca_bundle(argument):
    # Use the combined platform trust store, not a session CA copied into the image.
    candidate = argument
    if candidate is None and os.environ.get("CODEX_PROXY_CERT"):
        candidate = "/etc/ssl/certs/ca-certificates.crt"
    if candidate is None:
        return None
    path = Path(candidate).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"CA bundle not found: {path}")
    return path


def save_pin(image, image_recipe):
    PIN.parent.mkdir(parents=True, exist_ok=True)
    PIN.write_text(json.dumps({"image": image, "recipe": image_recipe}, indent=2) + "\n")


def build_image(args):
    config = settings()
    identifier = recipe()
    output = REPO / "build/container-image"
    output.mkdir(parents=True, exist_ok=True)
    command = [
        "docker",
        "buildx",
        "build",
        "--load",
        "--platform",
        config["platform"],
        "--file",
        "docker/Dockerfile",
        "--build-arg",
        f"BASE_IMAGE={config['base_image']}",
        "--build-arg",
        f"RECIPE={identifier}",
        "--tag",
        f"deepchat-dev:{identifier}",
        "--iidfile",
        output / "image-id",
    ]
    trust = ca_bundle(args.ca_bundle)
    if trust:
        command.extend(["--secret", f"id=proxy_ca,src={trust}"])
    run([*command, "."])
    image_id = (output / "image-id").read_text().strip()
    save_pin(image_id, identifier)
    print(f"Selected development image: {image_id}")


def pull_image(args):
    reference = args.reference or settings()["image"]
    if not reference:
        raise ValueError("No published image is pinned yet; use 'image build' or supply an @sha256 reference")
    require_digest(reference)
    run(["docker", "pull", "--platform", settings()["platform"], reference])
    metadata = run(
        ["docker", "image", "inspect", reference, "--format", '{{index .Config.Labels "io.deepchat.recipe"}}'],
        capture_output=True,
        text=True,
    )
    if metadata.stdout.strip() != recipe():
        raise ValueError("Published image does not match this checkout's toolchain recipe")
    save_pin(reference, recipe())


def pin_image(args):
    # Publish first, then validate the exact image before proposing a tracked lock update.
    pull_image(args)
    config = settings()
    config["image"] = args.reference
    (REPO / "tools/container-lock.json").write_text(json.dumps(config, indent=2) + "\n")


def selected_image():
    if not PIN.is_file():
        raise ValueError("Run python3 tools/dev.py setup to select/build the development image first")
    value = json.loads(PIN.read_text())
    if not isinstance(value, dict):
        raise ValueError("Local image selection must be a JSON object")
    if value["recipe"] != recipe():
        raise ValueError("Toolchain inputs changed; rebuild with 'image build' or pull the matching image")
    image = value["image"]
    if not isinstance(image, str) or not re.fullmatch(r"(?:sha256:[0-9a-f]{64}|[^\s@]+@sha256:[0-9a-f]{64})", image):
        raise ValueError("Local image selection must contain an immutable content ID or registry digest")
    return image


def execute(arguments, args):
    image = selected_image()
    command = [
        "docker",
        "run",
        "--rm",
        "--platform",
        settings()["platform"],
        "--user",
        f"{os.getuid()}:{os.getgid()}",
        "--mount",
        f"type=bind,src={REPO},dst=/workspace",
        "--workdir",
        "/workspace",
    ]
    if args.offline:
        command.extend(["--network", "none"])
    trust = ca_bundle(args.ca_bundle)
    if trust:
        command.extend(["--mount", f"type=bind,src={trust},dst=/run/deepchat-ca.pem,readonly"])
        for name in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "PIP_CERT", "GIT_SSL_CAINFO"):
            command.extend(["--env", f"{name}=/run/deepchat-ca.pem"])
    # Container paths are stable. Map selected absolute host filenames at the transport boundary.
    inner = []
    for argument in arguments:
        if Path(argument).is_absolute():
            path = Path(argument).resolve()
            if not path.is_relative_to(REPO):
                raise ValueError("Selected source path is outside the checkout")
            argument = str(Path("/workspace") / path.relative_to(REPO))
        inner.append(argument)
    run([*command, image, "python3", "tools/dev.py", "--native", *inner])
