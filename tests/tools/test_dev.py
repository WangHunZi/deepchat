"""Behavior checks for the development entry, without an ESP-IDF download."""

import argparse
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("deepchat_dev", ROOT / "tools/native.py")
dev = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dev)


class DevelopmentEntryTest(unittest.TestCase):
    def test_child_failure_is_the_cli_exit_status(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tools").mkdir()
            for name in ("dev.py", "native.py", "container.py", "sdk-lock.json"):
                (root / "tools" / name).write_bytes((ROOT / "tools" / name).read_bytes())
            binaries = root / ".venv/bin"
            binaries.mkdir(parents=True)
            (binaries / "python").symlink_to(sys.executable)
            cmake = binaries / "cmake"
            cmake.write_text("#!/bin/sh\nexit 17\n")
            cmake.chmod(0o755)
            result = subprocess.run(
                [sys.executable, root / "tools/dev.py", "--native", "build", "--target", "host"],
                capture_output=True,
                text=True,
                env=os.environ | {"DC_TOOL_ROOT": str(root), "DC_BUILD_ROOT": str(root / "build")},
            )
            self.assertEqual(result.returncode, 17, result.stderr)
            self.assertNotIn("ESP-IDF", result.stderr)

    def test_tools_suite_rejects_zero_tests(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tests = root / "tests/tools"
            tests.mkdir(parents=True)
            # Isolate discovery from the running suite's import cache.
            loader = unittest.TestLoader()
            with mock.patch.object(dev, "REPO", root), mock.patch.object(unittest, "defaultTestLoader", loader):
                with self.assertRaisesRegex(ValueError, "No tools tests"):
                    dev.test(argparse.Namespace(suite="tools"))

    def test_format_rejects_directory_and_external_file(self):
        with self.assertRaises(ValueError):
            dev.source_files([str(ROOT)])
        with tempfile.NamedTemporaryFile(suffix=".c") as outside:
            with self.assertRaises(ValueError):
                dev.source_files([outside.name])

    def test_format_accepts_selected_owned_file(self):
        file = ROOT / "apps/esp32s3/main/Main.c"
        self.assertEqual(dev.source_files([str(file)]), [file])

    def test_unconfirmed_board_cannot_be_built_as_deliverable(self):
        with self.assertRaisesRegex(ValueError, "unconfirmed"):
            dev.build(argparse.Namespace(target="esp32s3", board="xiao-esp32s3-plus", jobs=1))

    def test_rejects_modified_sdk_revision_without_resetting_it(self):
        with tempfile.TemporaryDirectory() as directory:
            sdk = Path(directory)
            subprocess.run(["git", "init", "--quiet", sdk], check=True)
            environment = os.environ | {
                "GIT_AUTHOR_NAME": "Fixture",
                "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
                "GIT_COMMITTER_NAME": "Fixture",
                "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
            }
            subprocess.run(
                ["git", "-C", sdk, "commit", "--quiet", "--allow-empty", "-m", "local SDK"], check=True, env=environment
            )
            before = subprocess.check_output(["git", "-C", sdk, "rev-parse", "HEAD"])
            with mock.patch.object(dev, "SDK", sdk):
                with self.assertRaisesRegex(ValueError, "revision differs"):
                    dev.check_sdk()
            self.assertEqual(subprocess.check_output(["git", "-C", sdk, "rev-parse", "HEAD"]), before)


if __name__ == "__main__":
    unittest.main()
