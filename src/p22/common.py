"""Paths, settings and provenance for the local replication pipeline."""

import hashlib
import json
from pathlib import Path

from settings import config

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(config("DATA_DIR"))
RAW = DATA / "authors" / "original"
CLEAN = DATA / "clean"
OUT = Path(config("OUTPUT_DIR")) / "replication"
CONFIG_PATH = ROOT / "config" / "replication.json"


def settings():
    """Load explicit baseline settings without silently changing paper samples."""
    return json.loads(CONFIG_PATH.read_text())


def sha256(path):
    """Hash file contents, not modification times."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, data):
    """Write readable structured metadata, rejecting invalid JSON numbers."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
