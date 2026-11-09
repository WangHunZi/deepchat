"""Build an isolated, content-addressed Xiaozhi source tree with the role patch."""

import hashlib
import io
import shutil
import tarfile
import tempfile
from pathlib import Path

import native


def prepare(source, revision):
    """The caller validates the pinned upstream; generated sources never modify it."""
    root = native.REPO
    patch = root / "patches/xiaozhi/pet-ui.patch"
    overlay = root / "src/xiaozhi"
    files = sorted(path for path in overlay.rglob("*") if path.is_file())
    lock = root / "config/xiaozhi/dependencies.lock"
    fingerprint = hashlib.sha256(revision.encode() + patch.read_bytes() + lock.read_bytes())
    for path in files:
        fingerprint.update(str(path.relative_to(overlay)).encode() + b"\0" + path.read_bytes())
    parent = native.BUILD_ROOT / "xiaozhi-pet" / fingerprint.hexdigest()[:20]
    destination = parent / "source"
    if not destination.is_dir():
        parent.mkdir(parents=True, exist_ok=True)
        archive = native.run(["git", "-C", source, "archive", revision], capture_output=True).stdout
        with tempfile.TemporaryDirectory(dir=parent, prefix="prepare-") as directory:
            temporary = Path(directory)
            with tarfile.open(fileobj=io.BytesIO(archive)) as contents:
                contents.extractall(temporary, filter="data")
            for path in files:
                output = temporary / path.relative_to(overlay)
                output.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, output)
            native.run(["git", "apply", "--directory=" + str(temporary.relative_to(root)), patch])
            shutil.copyfile(lock, temporary / "dependencies.lock")
            components = source / "managed_components"
            if components.is_dir():
                (temporary / "managed_components").symlink_to(components, target_is_directory=True)
            temporary.rename(destination)
    print(f"Role source: {destination}")
    return destination
