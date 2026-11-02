"""Build the initial study materials and ChartBook site; empirical pipeline pending."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOIT_CONFIG = {"backend": "sqlite3", "dep_file": ".doit-db.sqlite", "default_tasks": ["checks", "walkthrough", "site"]}


def task_checks():
    """Run existing scaffold utility tests and source-integrity tests."""
    return {"actions": [[sys.executable, "-m", "pytest", "-q"]], "verbosity": 2}


def task_walkthrough():
    """Create original-prose study notes without downloading copyrighted material."""
    return {
        "actions": [[sys.executable, "src/build_study_materials.py", "walkthrough"]],
        "file_dep": ["src/build_study_materials.py", "paper breakdown/walkthrough.json"],
        "targets": ["output/pdf/paper_walkthrough.pdf"],
    }


def task_reference_packet():
    """Verify/download the paper and create the local-only eight-exhibit attachment."""
    return {
        "actions": [[sys.executable, "src/build_study_materials.py", "packet"]],
        "file_dep": ["src/build_study_materials.py", "paper breakdown/exhibits.json"],
        "uptodate": [False],  # Recheck source integrity on each explicit request.
        "targets": ["output/pdf/answer_question.pdf"],
    }


def build_site():
    """Use the portable C locale for Sphinx on hosts without C.UTF-8."""
    executable = Path(sys.executable).parent / ("chartbook.exe" if sys.platform == "win32" else "chartbook")
    env = dict(os.environ, LC_ALL="C", LANG="C", LC_CTYPE="C")
    subprocess.run([str(executable), "docs", "build", "-f"], env=env, check=True)


def task_site():
    """Build the initial ChartBook site with project scope and provenance notes."""
    return {
        "actions": [build_site],
        "file_dep": ["dodo.py", "README.md", "chartbook.toml", *[str(p) for p in Path("docs_src/site").rglob("*.md")]],
        "targets": ["docs/index.html"],
    }
