#!/usr/bin/env python3
"""Shared local/CI entry. P0 supports host checks and build-only ESP32-S3 bringup."""

import argparse
import json
import os
import shutil
import subprocess
import sys
import unittest
import venv
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LOCK = json.loads((REPO / "tools/sdk-lock.json").read_text())
SDK = REPO / ".sdk/esp-idf"
SDK_TOOLS = REPO / ".sdk/tools"
VENV = REPO / ".venv"


def run(command, **kwargs):
    """Preserve the underlying tool's failure status, with inherited proxy and CA trust."""
    kwargs.setdefault("cwd", REPO)
    return subprocess.run([str(item) for item in command], check=True, **kwargs)


def python_path():
    return VENV / "bin/python"


def host_environment():
    if not python_path().is_file():
        raise ValueError("Run python3 tools/dev.py setup --host-only first")
    environment = os.environ.copy()
    environment["PATH"] = str(VENV / "bin") + os.pathsep + environment["PATH"]
    return environment


def check_sdk():
    if not (SDK / ".git").exists():
        raise ValueError("Run python3 tools/dev.py setup to install the pinned ESP-IDF")
    revision = run(["git", "-C", SDK, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    if revision != LOCK["idf_commit"]:
        raise ValueError(
            "ESP-IDF revision differs from sdk-lock.json; use the pinned checkout without discarding edits"
        )


def firmware_environment():
    check_sdk()
    environment = host_environment()
    compiler_bin = SDK_TOOLS / "tools/xtensa-esp-elf" / LOCK["tools"]["xtensa-esp-elf"] / "xtensa-esp-elf/bin"
    environment.update(
        IDF_PATH=str(SDK),
        IDF_TOOLS_PATH=str(SDK_TOOLS),
        IDF_PYTHON_ENV_PATH=str(VENV),
        IDF_TARGET=LOCK["target"],
        ESP_IDF_VERSION=LOCK["idf_tag"].removeprefix("v"),
        PYTHON=str(python_path()),
        ESP_ROM_ELF_DIR=str(SDK_TOOLS / "tools/esp-rom-elfs" / LOCK["tools"]["esp-rom-elfs"]),
    )
    environment["PATH"] = str(compiler_bin) + os.pathsep + environment["PATH"]
    return environment


def setup(args):
    if sys.platform not in ("linux", "darwin"):
        raise ValueError("P0 setup supports Linux/macOS; use WSL2 on Windows")
    actual_minor = f"{sys.version_info.major}.{sys.version_info.minor}"
    if actual_minor != LOCK["python_minor"]:
        raise ValueError(f"Use Python {LOCK['python_minor']} (CI: {LOCK['python_ci']})")
    if not VENV.exists():
        venv.EnvBuilder(with_pip=True).create(VENV)
    run(
        [
            python_path(),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "-r",
            REPO / "tools/requirements-host.txt",
        ]
    )
    if args.host_only:
        return
    SDK.parent.mkdir(parents=True, exist_ok=True)
    if not SDK.exists():
        run(["git", "clone", "--branch", LOCK["idf_tag"], "--depth", "1", LOCK["idf_repository"], SDK])
    check_sdk()
    changes = run(
        ["git", "-C", SDK, "status", "--porcelain", "--untracked-files=normal"], capture_output=True, text=True
    )
    if changes.stdout:
        raise ValueError("ESP-IDF has local changes; preserve them before running setup")
    run(["git", "-C", SDK, "submodule", "update", "--init", "--recursive", "--depth", "1", "--jobs", args.jobs])
    environment = host_environment()
    environment.update(IDF_PATH=str(SDK), IDF_TOOLS_PATH=str(SDK_TOOLS))
    run([python_path(), SDK / "tools/idf_tools.py", "install", *LOCK["tools"]], env=environment)
    run(
        [
            python_path(),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "-r",
            REPO / "tools/requirements-idf.txt",
        ]
    )
    # Keep upstream requirement checks enabled, using the reviewed constraints snapshot.
    SDK_TOOLS.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REPO / "tools/idf-constraints.txt", SDK_TOOLS / "espidf.constraints.v6.1.txt")
    run([python_path(), SDK / "tools/idf_tools.py", "check-python-dependencies"], env=firmware_environment())


def host_build(args):
    environment = host_environment()
    output = REPO / "build/host"
    run(["cmake", "-S", REPO, "-B", output, "-G", "Ninja", "-DCMAKE_BUILD_TYPE=Debug"], env=environment)
    run(["cmake", "--build", output, "--parallel", args.jobs], env=environment)


def build(args):
    if args.target == "host":
        host_build(args)
        return
    if args.board != "bringup":
        raise ValueError("P0 only supports --board bringup; XIAO pinout/Flash/PSRAM remain unconfirmed")
    environment = firmware_environment()
    environment["IDF_PY_BUILD_JOBS"] = str(args.jobs)
    output = REPO / "build/esp32s3-bringup"
    run(
        [
            python_path(),
            SDK / "tools/idf.py",
            "-C",
            REPO / "apps/esp32s3",
            "-B",
            output,
            "-D",
            f"SDKCONFIG={output / 'sdkconfig'}",
            "build",
        ],
        env=environment,
    )


def is_owned_source(relative):
    return relative.parts[0] in ("apps", "src", "include", "tests", "tools") and not any(
        part in ("managed_components", "third_party", "third_parties", "lib", "libs", "generated", "build")
        for part in relative.parts
    )


def source_files(paths):
    if paths:
        files = [Path(path).resolve() for path in paths]
        for file in files:
            if not file.is_file():
                raise ValueError(f"Source file does not exist: {file}")
            if not file.is_relative_to(REPO):
                raise ValueError("Format only project-owned files under apps/src/include/tests/tools")
            relative = file.relative_to(REPO)
            if not is_owned_source(relative):
                raise ValueError("Do not format dependency or generated files")
        return files
    result = run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], capture_output=True).stdout
    return sorted(
        REPO / os.fsdecode(path) for path in result.split(b"\0") if path and is_owned_source(Path(os.fsdecode(path)))
    )


def format_sources(args):
    environment = host_environment()
    version = run(["clang-format", "--version"], env=environment, capture_output=True, text=True).stdout.split()
    if LOCK["clang_format"] not in version:
        raise ValueError(f"Use clang-format {LOCK['clang_format']}; run setup --host-only")
    files = source_files(args.files)
    c_files = [file for file in files if file.suffix in (".c", ".h", ".cpp", ".hpp")]
    py_files = [file for file in files if file.suffix == ".py"]
    if c_files:
        flags = ["--dry-run", "--Werror"] if args.check else ["-i"]
        run(["clang-format", *flags, *c_files], env=environment)
    if py_files:
        run(["ruff", "check", *py_files], env=environment)
        run(["ruff", "format", *(["--check"] if args.check else []), *py_files], env=environment)


def test(args):
    if args.suite == "tools":
        suite = unittest.defaultTestLoader.discover(str(REPO / "tests/tools"))
        if suite.countTestCases() == 0:
            raise ValueError("No tools tests found")
        if not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful():
            raise ValueError("Tools tests failed")
        return
    host_build(args)
    run(
        [
            "ctest",
            "--test-dir",
            REPO / "build/host",
            "--output-on-failure",
            "--no-tests=error",
            "-L",
            f"^{args.suite}$",
        ],
        env=host_environment(),
    )


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--jobs", type=int, default=4, help="Build/submodule parallelism (default: 4)")
    commands = result.add_subparsers(dest="command", required=True)
    install = commands.add_parser("setup", help="Install pinned host tools and ESP-IDF")
    install.add_argument("--host-only", action="store_true", help="Do not download SDK/cross tools")
    install.set_defaults(action=setup)
    compile_command = commands.add_parser("build")
    compile_command.add_argument("--target", choices=["host", "esp32s3"], required=True)
    compile_command.add_argument("--board", default="bringup")
    compile_command.set_defaults(action=build)
    formatting = commands.add_parser("format")
    formatting.add_argument("--check", action="store_true")
    formatting.add_argument("files", nargs="*", help="Selected owned files; default: all owned sources")
    formatting.set_defaults(action=format_sources)
    tests = commands.add_parser("test")
    tests.add_argument("--suite", choices=["tools", "unit", "c-api-compat"], required=True)
    tests.set_defaults(action=test)
    return result


def main():
    args = parser().parse_args()
    if args.jobs < 1:
        print("error: --jobs must be positive", file=sys.stderr)
        return 2
    try:
        args.action(args)
    except subprocess.CalledProcessError as error:
        return error.returncode if error.returncode > 0 else 128 - error.returncode
    except (ValueError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
