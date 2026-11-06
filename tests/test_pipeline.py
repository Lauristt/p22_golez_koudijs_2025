"""Exercise clean builds, no-op runs, input/code changes and lost-target recovery."""

import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "_data/authors/original"


@pytest.mark.skipif(
    not RAW.exists(), reason="Run doit fetch to enable local end-to-end source tests"
)
def test_dependency_graph_and_published_baseline(tmp_path):
    for name in ["dodo.py", "pyproject.toml", "uv.lock"]:
        shutil.copy2(ROOT / name, tmp_path / name)
    shutil.copytree(ROOT / "config", tmp_path / "config")
    shutil.copytree(ROOT / "src/p22", tmp_path / "src/p22")
    shutil.copy2(ROOT / "src/settings.py", tmp_path / "src/settings.py")
    shutil.copytree(RAW, tmp_path / "_data/authors/original")
    shutil.copy2(
        ROOT / "_data/authors/mendeley_v1.zip",
        tmp_path / "_data/authors/mendeley_v1.zip",
    )
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "--allow-empty",
            "-qm",
            "fixture",
        ],
        cwd=tmp_path,
        check=True,
    )
    env = dict(
        os.environ,
        DATA_DIR=str(tmp_path / "_data"),
        OUTPUT_DIR=str(tmp_path / "_output"),
    )

    def build(*tasks):
        completed = subprocess.run(
            [sys.executable, "-m", "doit", *tasks],
            cwd=tmp_path,
            env=env,
            text=True,
            capture_output=True,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr
        return completed.stdout

    out = tmp_path / "_output/replication"
    assert ".  tables:history" in build("accept")
    baseline = pd.read_csv(out / "validation/summary.csv")
    assert baseline.recomputed_cells.sum() == 263
    assert baseline.differences.sum() == 0
    assert baseline.source_constants.sum() == 3
    assert not any(line.startswith(".  ") for line in build().splitlines())
    # A meaningful Excel source value changes only its dependent figure, not tables.
    workbook = tmp_path / "_data/authors/original/Data_Summary.xlsx"
    with ZipFile(workbook) as z:
        entries = {n: z.read(n) for n in z.namelist()}
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    xml = ET.fromstring(entries["xl/worksheets/sheet1.xml"])
    values = xml.findall(".//s:c/s:v", ns)
    value = next(v for v in values if v.text and v.text.startswith("0.34"))
    value.text = str(float(value.text) + 0.02)
    entries["xl/worksheets/sheet1.xml"] = ET.tostring(xml)
    with ZipFile(workbook, "w") as z:
        for n, content in entries.items():
            z.writestr(n, content)
    before = (out / "figure_data/figure_3_author_summary.csv").read_bytes()
    changed = build()
    assert ".  ingest:summary" in changed and ".  figures:summary" in changed
    assert ".  tables:" not in changed
    assert before != (out / "figure_data/figure_3_author_summary.csv").read_bytes()
    assert (
        "Data_Summary.xlsx"
        in json.loads((out / "provenance/latest.json").read_text())[
            "modified_author_files"
        ]
    )
    # Change a real Python calculation in the disposable copy, not the production code.
    module = tmp_path / "src/p22/portfolios.py"
    module.write_text(
        module.read_text()
        .replace("payout.mean() * 100", "payout.mean() * 101")
        .replace("payout.mean()*100", "payout.mean()*101")
    )
    before = (out / "figure_data/figure_3.csv").read_bytes()
    changed = build()
    assert ".  tables:portfolios" in changed and ".  figures:summary" in changed
    assert ".  tables:history" not in changed and ".  tables:strips" not in changed
    assert before != (out / "figure_data/figure_3.csv").read_bytes()
    assert pd.read_csv(out / "validation/summary.csv").differences.sum() > 0
    # Removal of one deliverable rebuilds its producer, even without source changes.
    (out / "tables/table_1.html").unlink()
    assert ".  tables:strips" in build()
    assert (out / "tables/table_1.html").exists()
    assert not any(line.startswith(".  ") for line in build().splitlines())
