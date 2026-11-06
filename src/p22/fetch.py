"""Download the pinned author package without overwriting local input edits."""

import json
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

from .common import DATA, RAW, ROOT


def fetch():
    """Fill missing package files and verify each against the reviewed version."""
    manifest = json.loads((ROOT / "config/authors_package.json").read_text())
    archive = DATA / "authors" / "mendeley_v1.zip"
    archive.parent.mkdir(parents=True, exist_ok=True)
    if not archive.exists():
        with urlopen(manifest["download_url"], timeout=90) as response:
            payload = response.read()
        temporary = archive.with_suffix(".part")
        temporary.write_bytes(payload)
        with ZipFile(temporary) as package:
            if package.testzip() is not None:
                raise ValueError("Downloaded ZIP is corrupt")
        temporary.replace(archive)
    RAW.mkdir(parents=True, exist_ok=True)
    with ZipFile(archive) as package:
        for item in package.infolist():
            name = Path(item.filename).name
            if name not in manifest["files"] or item.is_dir():
                continue
            target = RAW / name
            if target.exists():
                continue  # Never overwrite user-modified working inputs.
            content = package.read(item)
            import hashlib

            if hashlib.sha256(content).hexdigest() != manifest["files"][name]:
                raise ValueError(f"Unexpected package version: {name}")
            target.write_bytes(content)
    missing = [name for name in manifest["files"] if not (RAW / name).exists()]
    if missing:
        raise FileNotFoundError(missing)


if __name__ == "__main__":
    fetch()
