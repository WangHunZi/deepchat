"""Build an isolated Xiaozhi source tree with explicit board/role patches."""

import hashlib
import io
import shutil
import tarfile
import tempfile
from pathlib import Path

import native


def prepare(source, revision, *, pet=True, profile="reference-s3-lcd", display_test=False):
    """The caller validates the pinned upstream; generated sources never modify it."""
    root = native.REPO
    patches = [root / "patches/xiaozhi/pet-ui.patch", root / "patches/xiaozhi/manual-listening.patch"] if pet else []
    if profile == "xiao-esp32s3-plus-st7789":
        patches.append(root / "patches/xiaozhi/xiao-plus.patch")
    overlay = root / "src/xiaozhi"
    files = sorted(path for path in overlay.rglob("*") if path.is_file())
    lock = root / "config/xiaozhi/dependencies.lock"
    fingerprint = hashlib.sha256(revision.encode() + lock.read_bytes())
    fingerprint.update(f"{profile}:{pet}:{display_test}".encode())
    for patch in patches:
        fingerprint.update(patch.read_bytes())
    # sdkconfig 是持久构建输出；配置变更必须使用新目录，避免旧配置覆盖 defaults。
    configs = [root / f"config/xiaozhi/{profile}.defaults"]
    if display_test:
        configs.append(root / "config/xiaozhi/display-test.defaults")
    for config in configs:
        if config.is_file():
            fingerprint.update(config.read_bytes())
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
            for patch in patches:
                native.run(["git", "apply", "--directory=" + str(temporary.relative_to(root)), patch])
            shutil.copyfile(lock, temporary / "dependencies.lock")
            components = source / "managed_components"
            if components.is_dir():
                (temporary / "managed_components").symlink_to(components, target_is_directory=True)
            temporary.rename(destination)
    print(f"Isolated source ({profile}): {destination}")
    return destination
