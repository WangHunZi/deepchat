"""Pinned Xiaozhi integration; reference builds are not XIAO hardware validation."""

import json
import shutil

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
    defaults = [
        SOURCE / "sdkconfig.defaults",
        SOURCE / "sdkconfig.defaults.esp32s3",
        ROOT / "config/xiaozhi/reference-s3-lcd.defaults",
    ]
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
    build.set_defaults(action=build_reference)
