"""Pinned Xiaozhi integration; reference builds are not XIAO hardware validation."""

import json
import shutil
from pathlib import Path

import native

ROOT = native.REPO
SOURCE = ROOT / "third_party/xiaozhi-esp32"
XIAO_PROFILE = "xiao-esp32s3-plus-st7789"
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
    print(f"Xiaozhi source: {revision}; hardware unvalidated")


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
    if args.pet and not args.assets:
        raise ValueError("--pet requires --assets with a generated role resource pack")
    display_test = getattr(args, "display_test", False)
    if display_test and (args.profile != XIAO_PROFILE or args.pet or args.assets):
        raise ValueError("--display-test requires the XIAO profile and cannot use --pet or --assets")
    if args.profile == XIAO_PROFILE and not (display_test or args.pet):
        raise ValueError("The XIAO profile requires --display-test or --pet with --assets")
    check_source()
    prepare_dependencies()
    environment = native.firmware_environment()
    environment["IDF_PY_BUILD_JOBS"] = str(args.jobs)
    output = native.BUILD_ROOT / "xiaozhi-reference-s3-lcd"
    if args.assets:
        output = native.BUILD_ROOT / "xiaozhi-reference-s3-lcd-custom"
    source_tree = SOURCE
    if args.pet or args.profile == XIAO_PROFILE:
        import xiaozhi_overlay

        source_tree = xiaozhi_overlay.prepare(
            SOURCE, LOCK["revision"], pet=args.pet, profile=args.profile, display_test=display_test
        )
        output = source_tree.parent / "build"
    defaults = [
        source_tree / "sdkconfig.defaults",
        source_tree / "sdkconfig.defaults.esp32s3",
        ROOT / f"config/xiaozhi/{args.profile}.defaults",
    ]
    if display_test:
        defaults.append(ROOT / "config/xiaozhi/display-test.defaults")
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
            source_tree,
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
    if args.profile == XIAO_PROFILE:
        print(f"XIAO build complete: {output}; hardware validation pending; see docs/HARDWARE.md")
    else:
        print(f"Reference build complete: {output}; DO NOT flash as a XIAO firmware")


def register(commands):
    parser = commands.add_parser("xiaozhi", help=__doc__)
    operations = parser.add_subparsers(dest="xiaozhi_action", required=True)
    check = operations.add_parser("check", help="Verify the locked submodule and preserve local edits")
    check.set_defaults(action=lambda args: check_source())
    tests = operations.add_parser("test", help="Run real upstream FSM/LVGL/GIF host tests for the role UI")
    tests.set_defaults(action=test_pet)
    build = operations.add_parser("build", help="Build a reference or explicit XIAO hardware profile")
    build.add_argument("--profile", choices=[LOCK["reference_profile"], XIAO_PROFILE], required=True)
    build.add_argument("--assets", help="Optional local custom assets.bin; uses a separate reference build directory")
    build.add_argument("--pet", action="store_true", help="Build the isolated role UI patch; requires --assets")
    build.add_argument("--display-test", action="store_true", help="XIAO LCD pattern without audio/network startup")
    build.set_defaults(action=build_reference)


def test_pet(args):
    check_source()
    if not (SOURCE / "managed_components/lvgl__lvgl/CMakeLists.txt").is_file():
        raise ValueError("Build the reference once to cache the locked LVGL dependency before running role UI tests")
    output = native.BUILD_ROOT / "pet-tests"
    environment = native.host_environment()
    native.run(
        [
            "cmake",
            "-S",
            ROOT / "tests/pet",
            "-B",
            output,
            "-G",
            "Ninja",
            "-DCMAKE_BUILD_TYPE=Debug",
            "-DUPSTREAM_ROOT=" + str(SOURCE),
            "-DOVERLAY_ROOT=" + str(ROOT / "src/xiaozhi"),
        ],
        env=environment,
    )
    native.run(["cmake", "--build", output, "--parallel", args.jobs], env=environment)
    native.run(["ctest", "--test-dir", output, "--output-on-failure", "--no-tests=error"], env=environment)
