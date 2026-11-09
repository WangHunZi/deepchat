"""Pinned Xiaozhi integration; reference builds are not XIAO hardware validation."""

import json
import shutil
from pathlib import Path

import native

ROOT = native.REPO
SOURCE = ROOT / "third_party/xiaozhi-esp32"
LOCK = json.loads((ROOT / "tools/xiaozhi-lock.json").read_text())


def check_source():
    if not (SOURCE / ".git").exists():
        raise ValueError("Initialize the pinned source: git submodule update --init --depth 1")
    revision = native.run(["git", "-C", SOURCE, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    if revision != LOCK["revision"]:
        raise ValueError("Xiaozhi revision differs from xiaozhi-lock.json; preserve edits before switching revisions")
    changes = native.run(
        ["git", "-C", SOURCE, "status", "--porcelain", "--untracked-files=normal"], capture_output=True, text=True
    ).stdout
    if changes:
        raise ValueError("Xiaozhi has local source changes; preserve them before building the locked reference")
    print(f"Xiaozhi source: {revision}; reference only, hardware unvalidated")


def prepare_dependencies():
    locked = ROOT / "config/xiaozhi/dependencies.lock"
    generated = SOURCE / "dependencies.lock"
    if generated.exists() and generated.read_bytes() != locked.read_bytes():
        raise ValueError(
            "Local Xiaozhi dependencies.lock differs; preserve it before restoring the tracked reference lock"
        )
    if not generated.exists():
        shutil.copyfile(locked, generated)


def build_reference(args):
    check_source()
    prepare_dependencies()
    environment = native.firmware_environment()
    environment["IDF_PY_BUILD_JOBS"] = str(args.jobs)
    output = native.BUILD_ROOT / "xiaozhi-reference-s3-lcd"
    if args.assets:
        output = native.BUILD_ROOT / "xiaozhi-reference-s3-lcd-custom"
    defaults = [
        SOURCE / "sdkconfig.defaults",
        SOURCE / "sdkconfig.defaults.esp32s3",
        ROOT / "config/xiaozhi/reference-s3-lcd.defaults",
    ]
    if args.assets:
        source = Path(args.assets).resolve()
        if not source.is_file() or not 12 <= source.stat().st_size <= 8 * 1024 * 1024:
            raise ValueError("Custom assets must exist and fit the reference 8 MiB assets partition")
        output.mkdir(parents=True, exist_ok=True)
        asset_file = output / "input-assets.bin"
        shutil.copyfile(source, asset_file)
        custom_defaults = output / "custom-assets.defaults"
        custom_defaults.write_text(
            'CONFIG_FLASH_CUSTOM_ASSETS=y\nCONFIG_CUSTOM_ASSETS_FILE="' + str(asset_file) + '"\n'
        )
        defaults.append(custom_defaults)
    native.run(
        [
            native.python_path(),
            native.SDK / "tools/idf.py",
            "-C",
            SOURCE,
            "-B",
            output,
            "-D",
            f"SDKCONFIG={output / 'sdkconfig'}",
            "-D",
            "SDKCONFIG_DEFAULTS=" + ";".join(str(path) for path in defaults),
            "build",
        ],
        env=environment,
    )
    print(f"Reference build complete: {output}; DO NOT flash as a XIAO firmware")


def register(commands):
    parser = commands.add_parser("xiaozhi", help=__doc__)
    operations = parser.add_subparsers(dest="xiaozhi_action", required=True)
    check = operations.add_parser("check", help="Verify the locked submodule and preserve local edits")
    check.set_defaults(action=lambda args: check_source())
    build = operations.add_parser("build", help="Build the upstream ESP32-S3 LCD reference, not the final XIAO board")
    build.add_argument("--profile", choices=[LOCK["reference_profile"]], required=True)
    build.add_argument("--assets", help="Optional local custom assets.bin; uses a separate reference build directory")
    build.set_defaults(action=build_reference)
