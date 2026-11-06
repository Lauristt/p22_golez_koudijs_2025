"""Watch local source contents and rerun doit; stop with Ctrl-C. No remote writes."""

import hashlib
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from p22.common import RAW


def snapshot():
    paths = [
        ROOT / n for n in ["dodo.py", "pyproject.toml", "uv.lock", "src/settings.py"]
    ]
    paths += list((ROOT / "src/p22").glob("*.py")) + list(
        (ROOT / "config").glob("*.json")
    )
    if RAW.exists():
        paths += [p for p in RAW.iterdir() if p.is_file()]
    return {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.exists()
    }


def main():
    previous = None
    print(
        "Watching source files; rebuilding with doit. Ctrl-C stops. No files are pushed.",
        flush=True,
    )
    try:
        while True:
            current = snapshot()
            if current != previous:
                result = subprocess.run(
                    [sys.executable, "-m", "doit"], cwd=ROOT, env=os.environ.copy()
                )
                print(
                    "Build completed."
                    if result.returncode == 0
                    else "Build failed; fix source to retry.",
                    flush=True,
                )
                previous = current
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nWatcher stopped.")


if __name__ == "__main__":
    main()
