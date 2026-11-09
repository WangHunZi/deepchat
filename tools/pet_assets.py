"""Asset dependency setup, conversion commands and local preview hosting."""

import argparse
import functools
import http.server
import sys
import unittest
from pathlib import Path

import native
import xiaozhi

OUTPUT = native.REPO / "assets/generated/deepseek"
DEPENDENCIES = native.BUILD_ROOT / "asset-python"


def port_number(value):
    try:
        port = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Port must be an integer within 1..65535") from error
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("Port must be within 1..65535")
    return port


def setup(args):
    native.run(
        [
            native.python_path(),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--require-hashes",
            "--only-binary=:all:",
            "--no-deps",
            "--upgrade",
            "--target",
            DEPENDENCIES,
            "-r",
            native.REPO / "tools/requirements-assets.txt",
        ]
    )


def pipeline():
    if not DEPENDENCIES.is_dir():
        raise ValueError("Run python3 tools/dev.py assets setup first")
    sys.path.insert(0, str(DEPENDENCIES))
    import convert_assets

    return convert_assets


def build(args):
    xiaozhi.check_source()
    pipeline().build_bundle(
        native.REPO / "assets/pet/deepseek.json",
        native.REPO / "assets/local",
        native.REPO / "assets/sources.json",
        Path(args.base),
        OUTPUT,
        native.REPO,
    )
    print(f"Open {OUTPUT / 'index.html'} or run python3 tools/dev.py preview")


def check(args):
    xiaozhi.check_source()
    pipeline().check_bundle(OUTPUT, native.REPO)
    print("Converted GIFs, packed resources, hashes, dimensions and preview frames verified")


def test(args):
    pipeline()
    suite = unittest.defaultTestLoader.discover(str(native.REPO / "tests/assets"))
    if suite.countTestCases() == 0:
        raise ValueError("No asset tests found")
    if not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful():
        raise ValueError("Asset tests failed")


def preview(args):
    if not (OUTPUT / "index.html").is_file():
        raise ValueError("Run python3 tools/dev.py assets build first")
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(OUTPUT))
    with http.server.ThreadingHTTPServer((args.host, args.port), handler) as server:
        print(f"Preview: http://{args.host}:{server.server_port}/ (Ctrl-C to stop)", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


def register(commands):
    parser = commands.add_parser("assets", help="Convert local role assets using the upstream GIF and resource format")
    operations = parser.add_subparsers(required=True)
    for name, action in (("setup", setup), ("check", check), ("test", test), ("build", build)):
        command = operations.add_parser(name)
        command.set_defaults(action=action)
        if name == "build":
            command.add_argument(
                "--base", default=str(native.BUILD_ROOT / "xiaozhi-reference-s3-lcd/generated_assets.bin")
            )
    viewer = commands.add_parser("preview", help="Serve generated assets locally without Docker or new dependencies")
    viewer.add_argument("--host", default="127.0.0.1")
    viewer.add_argument("--port", type=port_number, default=8765, metavar="PORT")
    viewer.set_defaults(action=preview)
