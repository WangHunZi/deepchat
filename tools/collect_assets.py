"""Collect pinned third-party originals locally; no conversion or license grant."""

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def verify(data, entry):
    if len(data) != entry["size_bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
        raise ValueError(f"Asset does not match source lock: {entry['path']}")


def collect_pack(pack, destination, check=False):
    """Validate local files, or download missing originals from the source lock."""
    for entry in pack["files"]:
        target = destination / entry["path"]
        if target.exists():
            verify(target.read_bytes(), entry)
            print(f"Verified {target}")
            continue
        if check:
            raise FileNotFoundError(f"Missing asset: {target}; run collection without --check")
        with urllib.request.urlopen(entry["url"], timeout=60) as response:
            data = response.read(entry["size_bytes"] + 1)
        verify(data, entry)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        print(f"Downloaded {target}")


def main():
    catalog = json.loads((ROOT / "assets/sources.json").read_text(encoding="utf-8"))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", choices=list(catalog["packs"]), help="Default: collect both starter packs")
    parser.add_argument("--check", action="store_true", help="Check local bytes only; never access the network")
    args = parser.parse_args()
    for name, pack in catalog["packs"].items():
        if args.pack is None or args.pack == name:
            print(f"{name}: {pack['license_status']}")
            collect_pack(pack, ROOT / "assets/local" / name, args.check)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, urllib.error.URLError) as error:
        print(f"Asset collection failed: {error}", file=sys.stderr)
        sys.exit(1)
