"""Role source preparation preserves pinned upstream and rejects partial patches."""

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("overlay_native", ROOT / "tools/native.py")
native = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(native)
SPEC = importlib.util.spec_from_file_location("overlay_under_test", ROOT / "tools/xiaozhi_overlay.py")
overlay = importlib.util.module_from_spec(SPEC)
with mock.patch.dict(sys.modules, {"native": native}):
    SPEC.loader.exec_module(overlay)


class XiaozhiOverlayTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / "upstream"
        self.source.mkdir()
        (self.source / "hello.txt").write_text("original\n")
        (self.source / "board.txt").write_text("reference\n")
        (self.source / ".gitignore").write_text("managed_components/\n")
        environment = os.environ | {
            "GIT_AUTHOR_NAME": "Fixture",
            "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
            "GIT_COMMITTER_NAME": "Fixture",
            "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
        }
        subprocess.run(["git", "init", "--quiet", self.root], check=True)
        subprocess.run(["git", "init", "--quiet", self.source], check=True)
        subprocess.run(["git", "-C", self.source, "add", "."], check=True)
        subprocess.run(["git", "-C", self.source, "commit", "--quiet", "-m", "upstream"], env=environment, check=True)
        self.revision = subprocess.check_output(["git", "-C", self.source, "rev-parse", "HEAD"], text=True).strip()
        (self.source / "managed_components").mkdir()
        self.patch = self.root / "patches/xiaozhi/pet-ui.patch"
        self.patch.parent.mkdir(parents=True)
        self.patch.write_text("--- a/hello.txt\n+++ b/hello.txt\n@@ -1 +1 @@\n-original\n+role\n")
        header = self.root / "src/xiaozhi/main/Role.h"
        header.parent.mkdir(parents=True)
        header.write_text("// fixture overlay\n")
        lock = self.root / "config/xiaozhi/dependencies.lock"
        lock.parent.mkdir(parents=True)
        lock.write_text("locked dependencies fixture\n")
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(native, "REPO", self.root).start()
        mock.patch.object(native, "BUILD_ROOT", self.root / "build/container").start()

    def test_role_source_is_patched_without_modifying_pinned_upstream(self):
        prepared = overlay.prepare(self.source, self.revision)
        self.assertEqual((prepared / "hello.txt").read_text(), "role\n")
        self.assertEqual((prepared / "main/Role.h").read_text(), "// fixture overlay\n")
        self.assertEqual((prepared / "dependencies.lock").read_text(), "locked dependencies fixture\n")
        self.assertEqual((prepared / "managed_components").resolve(), self.source / "managed_components")
        self.assertEqual((self.source / "hello.txt").read_text(), "original\n")
        self.assertEqual(subprocess.check_output(["git", "-C", self.source, "status", "--porcelain"]), b"")
        self.assertEqual(overlay.prepare(self.source, self.revision), prepared)

    def test_patch_changes_get_a_fresh_build_source(self):
        previous = overlay.prepare(self.source, self.revision)
        self.patch.write_text(self.patch.read_text().replace("+role", "+updated"))
        current = overlay.prepare(self.source, self.revision)
        self.assertNotEqual(previous, current)
        self.assertEqual((previous / "hello.txt").read_text(), "role\n")
        self.assertEqual((current / "hello.txt").read_text(), "updated\n")

    def test_failed_patch_does_not_publish_partial_source(self):
        correct = self.patch.read_text()
        self.patch.write_text(correct.replace("-original", "-not-present"))
        with self.assertRaises(subprocess.CalledProcessError):
            overlay.prepare(self.source, self.revision)
        self.assertFalse(list((self.root / "build/container/xiaozhi-pet").glob("*/source")))
        self.assertEqual((self.source / "hello.txt").read_text(), "original\n")
        self.patch.write_text(correct)
        self.assertEqual((overlay.prepare(self.source, self.revision) / "hello.txt").read_text(), "role\n")

    def test_pet_build_requires_assets_before_toolchain_or_source_work(self):
        result = subprocess.run(
            [
                sys.executable,
                ROOT / "tools/dev.py",
                "--native",
                "xiaozhi",
                "build",
                "--profile",
                "reference-s3-lcd",
                "--pet",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("--pet requires --assets", result.stderr)

    def test_xiao_modes_apply_board_patch_and_keep_role_patch_opt_in(self):
        board_patch = self.patch.with_name("xiao-plus.patch")
        board_patch.write_text("--- a/board.txt\n+++ b/board.txt\n@@ -1 +1 @@\n-reference\n+xiao\n")
        pattern = overlay.prepare(
            self.source, self.revision, pet=False, profile="xiao-esp32s3-plus-st7789", display_test=True
        )
        pet = overlay.prepare(self.source, self.revision, profile="xiao-esp32s3-plus-st7789")
        self.assertNotEqual(pattern, pet)
        self.assertEqual((pattern / "board.txt").read_text(), "xiao\n")
        self.assertEqual((pattern / "hello.txt").read_text(), "original\n")
        self.assertEqual((pet / "board.txt").read_text(), "xiao\n")
        self.assertEqual((pet / "hello.txt").read_text(), "role\n")
        self.assertEqual((self.source / "board.txt").read_text(), "reference\n")

    def test_profile_defaults_changes_cannot_reuse_previous_sdkconfig(self):
        config = self.root / "config/xiaozhi/reference-s3-lcd.defaults"
        config.write_text("CONFIG_FIXTURE=old\n")
        previous = overlay.prepare(self.source, self.revision)
        config.write_text("CONFIG_FIXTURE=new\n")
        self.assertNotEqual(previous, overlay.prepare(self.source, self.revision))

    def test_display_test_defaults_changes_get_a_new_build(self):
        self.patch.with_name("xiao-plus.patch").write_text(
            "--- a/board.txt\n+++ b/board.txt\n@@ -1 +1 @@\n-reference\n+xiao\n"
        )
        config = self.root / "config/xiaozhi/display-test.defaults"
        config.write_text("CONFIG_DC_DISPLAY_TEST=y\n")
        kwargs = {"pet": False, "profile": "xiao-esp32s3-plus-st7789", "display_test": True}
        previous = overlay.prepare(self.source, self.revision, **kwargs)
        config.write_text("CONFIG_DC_DISPLAY_TEST=y\nCONFIG_FIXTURE=y\n")
        self.assertNotEqual(previous, overlay.prepare(self.source, self.revision, **kwargs))

    def test_invalid_hardware_modes_fail_before_source_or_toolchain_work(self):
        cases = [
            (["--profile", "reference-s3-lcd", "--display-test"], "--display-test requires the XIAO"),
            (["--profile", "xiao-esp32s3-plus-st7789"], "requires --display-test or --pet"),
            (
                ["--profile", "xiao-esp32s3-plus-st7789", "--display-test", "--assets", "nonexistent.bin"],
                "cannot use --pet or --assets",
            ),
            (
                ["--profile", "xiao-esp32s3-plus-st7789", "--display-test", "--pet", "--assets", "nonexistent.bin"],
                "cannot use --pet or --assets",
            ),
        ]
        for arguments, expected in cases:
            with self.subTest(arguments=arguments):
                result = subprocess.run(
                    [sys.executable, ROOT / "tools/dev.py", "--native", "xiaozhi", "build", *arguments],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 1)
                self.assertIn(expected, result.stderr)

    def test_dependency_lock_changes_cannot_reuse_a_stale_source_lock(self):
        previous = overlay.prepare(self.source, self.revision)
        lock = self.root / "config/xiaozhi/dependencies.lock"
        lock.write_text("updated dependencies\n")
        current = overlay.prepare(self.source, self.revision)
        self.assertNotEqual(previous, current)
        self.assertEqual((current / "dependencies.lock").read_text(), "updated dependencies\n")
        self.assertEqual((previous / "dependencies.lock").read_text(), "locked dependencies fixture\n")


if __name__ == "__main__":
    unittest.main()
