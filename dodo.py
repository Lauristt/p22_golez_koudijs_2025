"""Content-dependent Python replication; raw data and generated results stay local."""

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from p22.common import CLEAN, OUT, RAW
from p22.ingest import GROUP_FILES

DOIT_CONFIG = {
    "backend": "sqlite3",
    "dep_file": os.environ.get("P22_DOIT_DB", ".doit-db.sqlite"),
    "default_tasks": ["replicate"],
    "check_file_uptodate": "md5",
}
COMMON = [
    "src/p22/common.py",
    "src/settings.py",
    "config/replication.json",
    "pyproject.toml",
    "uv.lock",
    "dodo.py",
]
NUMERIC = ["src/p22/econometrics.py", "src/p22/output.py", str(RAW / "olsnw.m")]
TABLES = [1, 2, 4, 5, 6, 7]


def run(stage, group=None):
    """Use this environment's interpreter and explicit import path."""
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    subprocess.run(
        [sys.executable, "-m", "p22.run", stage, *([group] if group else [])],
        cwd=ROOT,
        env=env,
        check=True,
    )


def stage(name, deps, targets, task_dep=(), group=None):
    return {
        "actions": [(run, [name, group])],
        "file_dep": list(map(str, [*COMMON, "src/p22/run.py", *deps])),
        "targets": list(map(str, targets)),
        "task_dep": list(task_dep),
        "verbosity": 2,
    }


def table_targets(numbers):
    return [
        OUT / f"tables/table_{n}.{ext}"
        for n in numbers
        for ext in ["csv", "html", "tex"]
    ]


def figure_targets(names):
    return [OUT / f"figures/{name}.{ext}" for name in names for ext in ["png", "svg"]]


def task_fetch():
    """Recover missing files from pinned Mendeley v1; never overwrite local edits."""
    files = json.loads((ROOT / "config/authors_package.json").read_text())["files"]
    return stage(
        "fetch",
        ["config/authors_package.json", "src/p22/fetch.py"],
        [RAW / name for name in files],
    )


def cleaned(group):
    if group == "history":
        return [CLEAN / (Path(n).stem + ".parquet") for n in GROUP_FILES[group]]
    return [
        CLEAN / ("author_summary.parquet" if group == "summary" else group + ".parquet")
    ]


def task_ingest():
    """Normalize each independent source group to Parquet."""
    for group, files in GROUP_FILES.items():
        task = stage(
            "ingest",
            ["src/p22/ingest.py", *[RAW / n for n in files]],
            cleaned(group),
            ["fetch"],
            group,
        )
        yield {"name": group, **task}


def task_tables():
    """Recompute only tables affected by data, analysis code or configuration changes."""
    mapping = {
        "strips": ([1, 2], ["Table_1_2_Dividend_Strip.m"]),
        "history": ([4, 5], ["Table_4_Time_Series.m", "Table_5_Time_Series.m"]),
        "portfolios": ([6, 7], ["Table_6_7_Cross_Section.m"]),
    }
    for group, (numbers, originals) in mapping.items():
        yield {
            "name": group,
            **stage(
                group,
                [
                    f"src/p22/{group}.py",
                    *NUMERIC,
                    *cleaned(group),
                    *[RAW / n for n in originals],
                ],
                [*table_targets(numbers), OUT / f"diagnostics/{group}.json"],
                [f"ingest:{group}"],
            ),
        }


def task_figures():
    """Figure 3 depends on computed tables, so estimates cannot become stale."""
    yield {
        "name": "payout",
        **stage(
            "payout",
            [
                "src/p22/figures.py",
                CLEAN / "Data_US_1871_2022.parquet",
                RAW / "Figure_1_2_Time_Series.m",
            ],
            [*figure_targets(["figure_1"]), OUT / "figure_data/figure_1.csv"],
            ["ingest:history"],
        ),
    }
    yield {
        "name": "summary",
        **stage(
            "summary",
            [
                "src/p22/figures.py",
                "src/p22/econometrics.py",
                *table_targets([4, 5, 6, 7]),
                *cleaned("summary"),
                RAW / "Figure_3_Summary.m",
            ],
            [
                *figure_targets(["figure_3", "figure_3_author_summary"]),
                *[
                    OUT / f"figure_data/{n}.csv"
                    for n in ["figure_3", "figure_3_author_summary"]
                ],
                *[
                    OUT / f"diagnostics/{n}.json"
                    for n in ["figure_3", "figure_3_author_summary"]
                ],
            ],
            ["tables:history", "tables:portfolios", "ingest:summary"],
        ),
    }


VALIDATION = [
    OUT / f"validation/{n}"
    for n in [
        "published_comparison.csv",
        "published_comparison.html",
        "summary.csv",
        "summary.json",
        "data_checks.json",
    ]
]


def task_validate():
    """Report published-value differences and fail on broken data identities."""
    return stage(
        "validate",
        [
            "src/p22/validation.py",
            "src/p22/figures.py",
            "src/p22/output.py",
            "config/published_benchmarks.json",
            *table_targets(TABLES),
            OUT / "figure_data/figure_3.csv",
            *[p for group in GROUP_FILES for p in cleaned(group)],
        ],
        [*VALIDATION, *figure_targets(["validation"])],
        ["tables", "figures"],
    )


def task_report():
    """Build a local HTML exhibit report with full-precision exports and caveats."""
    return stage(
        "report",
        [
            "src/p22/validation.py",
            "src/p22/output.py",
            *table_targets(TABLES),
            *VALIDATION,
            *figure_targets(
                ["figure_1", "figure_3", "figure_3_author_summary", "validation"]
            ),
        ],
        [OUT / "index.html"],
        ["validate"],
    )


def task_provenance():
    """Append a successful build's input/code/output hashes to local history."""
    files = json.loads((ROOT / "config/authors_package.json").read_text())["files"]
    return stage(
        "provenance",
        [
            *sorted((ROOT / "src/p22").glob("*.py")),
            *sorted((ROOT / "config").glob("*.json")),
            *[RAW / n for n in files],
            OUT / "index.html",
            *VALIDATION,
            *table_targets(TABLES),
            *figure_targets(
                ["figure_1", "figure_3", "figure_3_author_summary", "validation"]
            ),
        ],
        [OUT / "provenance/latest.json", OUT / "provenance/build_history.jsonl"],
        ["report"],
    )


def task_replicate():
    """Build all assigned exhibits, validation report and hash history."""
    return {"actions": None, "task_dep": ["provenance"]}


def accept():
    """Strict frozen-baseline acceptance, separate from experimental rebuilds."""
    summary = json.loads((OUT / "validation/summary.json").read_text())
    if not summary["data_checks_passed"] or any(
        t["differences"] for t in summary["table_checks"]
    ):
        raise RuntimeError(
            "Published baseline acceptance failed; inspect the validation report"
        )
    print(
        "Baseline accepted: 263 recomputed numeric cells; 3 supplied constants excluded."
    )


def task_accept():
    return {"actions": [accept], "task_dep": ["replicate"]}


def task_checks():
    """Run numerical and dependency-invalidation tests."""
    return {"actions": [[sys.executable, "-m", "pytest", "-q"]], "verbosity": 2}


def build_site():
    executable = Path(sys.executable).parent / (
        "chartbook.exe" if sys.platform == "win32" else "chartbook"
    )
    env = dict(os.environ, LC_ALL="C", LANG="C", LC_CTYPE="C")
    subprocess.run([str(executable), "docs", "build", "-f"], env=env, check=True)


def task_site():
    """Build the separate ChartBook documentation site."""
    return {
        "actions": [build_site],
        "file_dep": [
            "dodo.py",
            "README.md",
            "chartbook.toml",
            *map(str, Path("docs_src/site").rglob("*.md")),
        ],
        "targets": ["docs/index.html"],
    }
