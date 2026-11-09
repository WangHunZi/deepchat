"""Source download and offline integrity requirements."""

import hashlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SPEC = importlib.util.spec_from_file_location(
    "collect_assets", Path(__file__).resolve().parents[2] / "tools/collect_assets.py"
)
assets = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(assets)


class AssetCollectionTest(unittest.TestCase):
    def setUp(self):
        self.data = b"asset fixture"
        self.entry = {
            "path": "previews/fixture.gif",
            "url": "https://example.invalid/fixed-revision/fixture.gif",
            "size_bytes": len(self.data),
            "sha256": hashlib.sha256(self.data).hexdigest(),
        }
        self.pack = {"files": [self.entry]}

    def test_download_preserves_original_bytes_and_offline_check_never_downloads(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            with mock.patch.object(assets.urllib.request, "urlopen", return_value=io.BytesIO(self.data)):
                assets.collect_pack(self.pack, destination)
            self.assertEqual((destination / self.entry["path"]).read_bytes(), self.data)
            with mock.patch.object(assets.urllib.request, "urlopen") as network:
                assets.collect_pack(self.pack, destination, check=True)
                assets.collect_pack(self.pack, destination)
                network.assert_not_called()

    def test_invalid_download_is_not_saved(self):
        for data in (b"x" * len(self.data), self.data + b"extra"):
            with self.subTest(data=data), tempfile.TemporaryDirectory() as directory:
                destination = Path(directory)
                with mock.patch.object(assets.urllib.request, "urlopen", return_value=io.BytesIO(data)):
                    with self.assertRaisesRegex(ValueError, "does not match"):
                        assets.collect_pack(self.pack, destination)
                self.assertFalse((destination / self.entry["path"]).exists())

    def test_offline_check_reports_missing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.object(assets.urllib.request, "urlopen") as network:
                with self.assertRaises(FileNotFoundError):
                    assets.collect_pack(self.pack, Path(directory), check=True)
                network.assert_not_called()

    def test_changed_local_file_is_preserved_and_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            target = destination / self.entry["path"]
            target.parent.mkdir(parents=True)
            target.write_bytes(b"local edit")
            with mock.patch.object(assets.urllib.request, "urlopen") as network:
                with self.assertRaisesRegex(ValueError, "does not match"):
                    assets.collect_pack(self.pack, destination)
                network.assert_not_called()
            self.assertEqual(target.read_bytes(), b"local edit")


if __name__ == "__main__":
    unittest.main()
