"""Pinned upstream boundary and unsupported-board behavior."""

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


native = load_module("xiaozhi_native", ROOT / "tools/native.py")
with mock.patch.dict(sys.modules, {"native": native}):
    xiaozhi = load_module("xiaozhi_under_test", ROOT / "tools/xiaozhi.py")


class XiaozhiSourceTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.source = Path(self.directory.name)
        self.file = self.source / "source.txt"
        self.file.write_text("original\n")
        environment = os.environ | {
            "GIT_AUTHOR_NAME": "Fixture",
            "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
            "GIT_COMMITTER_NAME": "Fixture",
            "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
        }
        subprocess.run(["git", "init", "--quiet", self.source], check=True)
        subprocess.run(["git", "-C", self.source, "add", "source.txt"], check=True)
        subprocess.run(["git", "-C", self.source, "commit", "--quiet", "-m", "source"], env=environment, check=True)
        self.revision = subprocess.check_output(["git", "-C", self.source, "rev-parse", "HEAD"], text=True).strip()

    def test_locked_clean_source_is_accepted(self):
        with (
            mock.patch.object(xiaozhi, "SOURCE", self.source),
            mock.patch.object(xiaozhi, "LOCK", {"revision": self.revision}),
        ):
            xiaozhi.check_source()

    def test_local_edits_are_rejected_and_preserved(self):
        self.file.write_text("local edit\n")
        with (
            mock.patch.object(xiaozhi, "SOURCE", self.source),
            mock.patch.object(xiaozhi, "LOCK", {"revision": self.revision}),
        ):
            with self.assertRaisesRegex(ValueError, "local source changes"):
                xiaozhi.check_source()
        self.assertEqual(self.file.read_text(), "local edit\n")

    def test_different_revision_is_rejected_without_reset(self):
        with (
            mock.patch.object(xiaozhi, "SOURCE", self.source),
            mock.patch.object(xiaozhi, "LOCK", {"revision": "0" * 40}),
        ):
            with self.assertRaisesRegex(ValueError, "revision differs"):
                xiaozhi.check_source()
        current = subprocess.check_output(["git", "-C", self.source, "rev-parse", "HEAD"], text=True).strip()
        self.assertEqual(current, self.revision)

    def test_unconfirmed_xiao_profile_is_rejected_before_build(self):
        result = subprocess.run(
            [sys.executable, ROOT / "tools/dev.py", "--native", "xiaozhi", "build", "--profile", "xiao-esp32s3-plus"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid choice", result.stderr)

    def test_missing_generated_lock_is_restored_from_tracked_bytes(self):
        locked = self.source / "config/xiaozhi/dependencies.lock"
        locked.parent.mkdir(parents=True)
        locked.write_bytes(b"locked fixture\n")
        target = self.source / "upstream"
        target.mkdir()
        with mock.patch.object(xiaozhi, "ROOT", self.source), mock.patch.object(xiaozhi, "SOURCE", target):
            xiaozhi.prepare_dependencies()
        self.assertEqual((target / "dependencies.lock").read_bytes(), locked.read_bytes())

    def test_different_generated_lock_is_preserved(self):
        locked = self.source / "config/xiaozhi/dependencies.lock"
        locked.parent.mkdir(parents=True)
        locked.write_bytes(b"locked fixture\n")
        generated = self.source / "dependencies.lock"
        generated.write_bytes(b"local resolution\n")
        with mock.patch.object(xiaozhi, "ROOT", self.source), mock.patch.object(xiaozhi, "SOURCE", self.source):
            with self.assertRaisesRegex(ValueError, "dependencies.lock differs"):
                xiaozhi.prepare_dependencies()
        self.assertEqual(generated.read_bytes(), b"local resolution\n")


if __name__ == "__main__":
    unittest.main()
