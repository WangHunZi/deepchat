"""Container transport contracts, independent of a Docker daemon or SDK."""

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("deepchat_container", ROOT / "tools/container.py")
container = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(container)
IMAGE_ID = "sha256:" + "1" * 64
REGISTRY_IMAGE = "ghcr.io/example/deepchat@sha256:" + "2" * 64


class ContainerBoundaryTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for name in container.INPUTS:
            file = self.root / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text("recipe fixture\n")
        config = self.root / "tools/container-lock.json"
        config.write_text(json.dumps({"base_image": REGISTRY_IMAGE, "platform": "linux/amd64", "image": None}))
        self.pin = self.root / "config/local/container-image.json"
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(container, "REPO", self.root).start()
        mock.patch.object(container, "PIN", self.pin).start()

    def test_missing_pin_requires_explicit_setup(self):
        with self.assertRaisesRegex(ValueError, "setup"):
            container.selected_image()

    def test_only_immutable_image_references_are_accepted(self):
        for image in (IMAGE_ID, REGISTRY_IMAGE):
            with self.subTest(image=image):
                container.save_pin(image, container.recipe())
                self.assertEqual(container.selected_image(), image)
        for image in ("deepchat-dev:latest", "ghcr.io/example/deepchat:v1", "sha256:123", ""):
            with self.subTest(image=image):
                container.save_pin(image, container.recipe())
                with self.assertRaises(ValueError):
                    container.selected_image()
        with self.assertRaises(ValueError):
            container.require_digest("python:latest")

    def test_recipe_change_invalidates_the_selected_image(self):
        container.save_pin(IMAGE_ID, container.recipe())
        (self.root / "tools/requirements-host.txt").write_text("changed dependency\n")
        with self.assertRaisesRegex(ValueError, "Toolchain inputs changed"):
            container.selected_image()

    def test_run_uses_callers_identity_and_no_docker_socket_or_sdk_mount(self):
        container.save_pin(IMAGE_ID, container.recipe())
        args = argparse.Namespace(offline=True, ca_bundle=None)
        with (
            mock.patch.object(container, "run", return_value=subprocess.CompletedProcess([], 0, stdout="[]")) as run,
            mock.patch.object(os, "getuid", return_value=1234),
            mock.patch.object(os, "getgid", return_value=2345),
            mock.patch.dict(os.environ, {}, clear=True),
        ):
            container.execute(["build", "--target", "host"], args)
        command = [str(value) for value in run.call_args.args[0]]
        self.assertEqual(command[command.index("--user") + 1], "1234:2345")
        self.assertEqual(command[command.index("--network") + 1], "none")
        mounts = [command[index + 1] for index, item in enumerate(command) if item == "--mount"]
        self.assertIn(f"type=bind,src={self.root},dst=/workspace", mounts)
        self.assertFalse(any("docker.sock" in value or ".sdk" in value or ".venv" in value for value in mounts))
        self.assertIn(IMAGE_ID, command)
        self.assertIn("--native", command)

    def test_selected_absolute_path_is_mapped_but_external_path_is_rejected(self):
        container.save_pin(IMAGE_ID, container.recipe())
        args = argparse.Namespace(offline=True, ca_bundle=None)
        source = self.root / "tools/native.py"
        with (
            mock.patch.object(container, "run", return_value=subprocess.CompletedProcess([], 0, stdout="[]")) as run,
            mock.patch.dict(os.environ, {}, clear=True),
        ):
            container.execute(["format", "--check", str(source)], args)
        self.assertIn("/workspace/tools/native.py", run.call_args.args[0])
        with mock.patch.object(container, "run", return_value=subprocess.CompletedProcess([], 0, stdout="[]")) as run:
            with self.assertRaisesRegex(ValueError, "outside"):
                container.execute(["format", str(self.root.parent / "outside.c")], args)
            self.assertFalse(any("run" in call.args[0] for call in run.call_args_list))

    def test_pull_with_wrong_recipe_preserves_the_previous_selection(self):
        container.save_pin(IMAGE_ID, container.recipe())
        previous = self.pin.read_bytes()
        tracked = (self.root / "tools/container-lock.json").read_bytes()
        wrong = subprocess.CompletedProcess([], 0, stdout="different recipe\n")
        with mock.patch.object(container, "run", return_value=wrong):
            with self.assertRaisesRegex(ValueError, "does not match"):
                container.pull_image(argparse.Namespace(reference=REGISTRY_IMAGE))
        self.assertEqual(self.pin.read_bytes(), previous)
        self.assertEqual((self.root / "tools/container-lock.json").read_bytes(), tracked)
        self.assertEqual(container.selected_image(), IMAGE_ID)

    def test_released_pin_records_and_selects_the_validated_digest(self):
        matching = subprocess.CompletedProcess([], 0, stdout=container.recipe() + "\n")
        with mock.patch.object(container, "run", return_value=matching):
            container.pin_image(argparse.Namespace(reference=REGISTRY_IMAGE))
        tracked = json.loads((self.root / "tools/container-lock.json").read_text())
        self.assertEqual(tracked["image"], REGISTRY_IMAGE)
        self.assertEqual(container.selected_image(), REGISTRY_IMAGE)

    def test_captured_git_error_remains_visible_with_its_exit_status(self):
        tools = self.root / "tools"
        for name in (
            "dev.py",
            "native.py",
            "container.py",
            "xiaozhi.py",
            "xiaozhi-lock.json",
            "pet_assets.py",
            "sdk-lock.json",
        ):
            (tools / name).write_bytes((ROOT / "tools" / name).read_bytes())
        binaries = self.root / ".venv/bin"
        binaries.mkdir(parents=True)
        (binaries / "python").symlink_to(sys.executable)
        formatter = binaries / "clang-format"
        formatter.write_text("#!/bin/sh\nprintf 'clang-format version 18.1.8\\n'\n")
        formatter.chmod(0o755)
        git = binaries / "git"
        git.write_text("#!/bin/sh\nprintf 'fixture repository ownership failure\\n' >&2\nexit 128\n")
        git.chmod(0o755)
        environment = os.environ | {
            "DC_TOOL_ROOT": str(self.root),
            "DC_BUILD_ROOT": str(self.root / "build"),
            "PATH": str(binaries) + os.pathsep + os.environ["PATH"],
        }
        entries = ([tools / "dev.py", "--native"], [tools / "native.py"])
        for entry in entries:
            with self.subTest(entry=entry):
                result = subprocess.run(
                    [sys.executable, *entry, "format", "--check"],
                    env=environment,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 128)
                self.assertIn("fixture repository ownership failure", result.stderr)

    def test_docker_failure_is_preserved_by_the_public_cli(self):
        tools = self.root / "tools"
        for name in (
            "dev.py",
            "native.py",
            "container.py",
            "xiaozhi.py",
            "xiaozhi-lock.json",
            "pet_assets.py",
            "sdk-lock.json",
        ):
            (tools / name).write_bytes((ROOT / "tools" / name).read_bytes())
        container.save_pin(IMAGE_ID, container.recipe())
        binaries = self.root / "bin"
        binaries.mkdir()
        docker = binaries / "docker"
        docker.write_text("#!/bin/sh\nexit 23\n")
        docker.chmod(0o755)
        environment = os.environ | {"PATH": str(binaries) + os.pathsep + os.environ["PATH"]}
        result = subprocess.run(
            [sys.executable, tools / "dev.py", "--offline", "build", "--target", "host"],
            env=environment,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 23, result.stderr)


if __name__ == "__main__":
    unittest.main()
