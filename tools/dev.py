#!/usr/bin/env python3
"""Shared container entry; native mode is retained for image maintenance."""

import subprocess
import sys

import container
import native
import pet_assets
import xiaozhi


def main():
    parser, commands = native.parser()
    xiaozhi.register(commands)
    pet_assets.register(commands)
    parser.description = __doc__
    parser.add_argument("--native", action="store_true", help="Run directly (image maintenance/inside container)")
    parser.add_argument("--offline", action="store_true", help="Disable network in the development container")
    parser.add_argument("--ca-bundle", help="Combined CA bundle for builds/runs behind an HTTPS proxy")
    image = commands.add_parser("image", help="Build or select an immutable development image")
    operations = image.add_subparsers(dest="image_action", required=True)
    operations.add_parser("build")
    pull = operations.add_parser("pull")
    pull.add_argument("reference", nargs="?")
    pin = operations.add_parser("pin", help="Validate and write a released digest to the tracked lock")
    pin.add_argument("reference")
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be positive")
    try:
        if args.command == "image":
            if args.image_action == "build":
                container.build_image(args)
            elif args.image_action == "pull":
                container.pull_image(args)
            else:
                container.pin_image(args)
        elif args.native or args.command == "preview":
            args.action(args)
        elif args.command == "setup":
            if args.host_only:
                raise ValueError("--host-only is for --native mode; container setup prepares the complete toolchain")
            if container.settings()["image"]:
                args.reference = None
                container.pull_image(args)
            else:
                container.build_image(args)
        else:
            # Remove transport-only flags before invoking the same interface inside the image.
            arguments = sys.argv[1:]
            inner = []
            index = 0
            while index < len(arguments):
                argument = arguments[index]
                if argument == "--offline":
                    index += 1
                elif argument == "--ca-bundle":
                    index += 2
                elif argument.startswith("--ca-bundle="):
                    index += 1
                else:
                    inner.append(argument)
                    index += 1
            container.execute(inner, args)
    except subprocess.CalledProcessError as error:
        if error.stderr:
            detail = error.stderr.decode(errors="replace") if isinstance(error.stderr, bytes) else error.stderr
            print(detail, file=sys.stderr, end="" if detail.endswith("\n") else "\n")
        return error.returncode if error.returncode > 0 else 128 - error.returncode
    except (ValueError, OSError, KeyError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
