"""Audit published benchmarks, data identities and build provenance without hiding differences."""

import json
import platform
import subprocess
from datetime import datetime, timezone
from html import escape

import numpy as np
import pandas as pd

from .common import CLEAN, OUT, RAW, ROOT, settings, sha256, write_json
from .output import STYLE, TABLE_INFO


def validate():
    """Compare every published numeric table cell and report unrecomputed constants separately."""
    OUT.joinpath("validation").mkdir(parents=True, exist_ok=True)
    benchmark = json.loads((ROOT / "config/published_benchmarks.json").read_text())
    records = []
    for number, values in benchmark["tables"].items():
        expected = np.array(values, dtype=float)
        actual = pd.read_csv(OUT / f"tables/table_{number}.csv", index_col=0)
        if actual.shape != expected.shape:
            raise ValueError(f"Table {number} shape mismatch")
        for i, row in enumerate(actual.index):
            for j, col in enumerate(actual.columns):
                value = float(actual.iloc[i, j])
                ref = float(expected[i, j])
                constant = number == "4" and i == 9
                tolerance = (
                    0
                    if number == "6" and i in [1, 2]
                    else benchmark["absolute_tolerance"]
                )
                both_nan = np.isnan(value) and np.isnan(ref)
                passed = bool(
                    both_nan
                    or (
                        np.isfinite(value)
                        and np.isfinite(ref)
                        and abs(value - ref) <= tolerance
                    )
                )
                records.append(
                    {
                        "table": int(number),
                        "statistic": row,
                        "sample": col,
                        "python": value,
                        "published": ref,
                        "difference": value - ref,
                        "tolerance": tolerance,
                        "within_tolerance": passed,
                        "independent": not constant,
                        "status": "source constant, not recomputed"
                        if constant
                        else (
                            "not applicable"
                            if both_nan
                            else ("within rounding" if passed else "difference")
                        ),
                    }
                )
    comparison = pd.DataFrame(records)
    comparison.to_csv(OUT / "validation/published_comparison.csv", index=False)
    comparison.to_html(
        OUT / "validation/published_comparison.html",
        index=False,
        float_format=lambda x: f"{x:.6f}",
        na_rep="—",
        border=0,
    )
    counts = []
    for num, g in comparison.groupby("table"):
        computed = g[g.independent & g.published.notna()]
        counts.append(
            {
                "table": int(num),
                "recomputed_cells": len(computed),
                "within_tolerance": int(computed.within_tolerance.sum()),
                "differences": int((~computed.within_tolerance).sum()),
                "source_constants": int((~g.independent).sum()),
            }
        )
    pd.DataFrame(counts).to_csv(OUT / "validation/summary.csv", index=False)
    checks = data_checks()
    write_json(OUT / "validation/data_checks.json", checks)
    write_json(
        OUT / "validation/summary.json",
        {
            "table_checks": counts,
            "data_checks_passed": all(c["passed"] for c in checks),
            "benchmark_tolerance": benchmark["absolute_tolerance"],
            "baseline_end_year": settings()["baseline_end_year"],
            "note": "Benchmark differences are reported, not optimized away. The strict acceptance command fails on any independently calculated discrepancy.",
        },
    )
    plot_validation(pd.DataFrame(counts))
    if not all(c["passed"] for c in checks):
        raise ValueError("Data identity/coverage checks failed; see data_checks.json")


def data_checks():
    """Check independently meaningful source identities and sample integrity."""
    checks = []

    def add(name, passed, detail):
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    strips = pd.read_parquet(CLEAN / "strips.parquet")
    cpi = strips.CPI.to_numpy()
    inflation = cpi[1:] / cpi[:-1] - 1
    error = float(np.max(abs(inflation - strips.Inflation.to_numpy()[1:])))
    add(
        "Strip inflation reconciles to CPI",
        error < 1e-10,
        f"maximum absolute difference {error:.3g}",
    )
    portfolios = pd.read_parquet(CLEAN / "portfolios.parquet")
    pivot = portfolios.pivot(index="year", columns="portfolio", values="n_stocks")
    add(
        "Tercile counts reconcile to All",
        np.array_equal(pivot[["Low", "Medium", "High"]].sum(axis=1), pivot.All),
        "Eligible stock counts sum in every year",
    )
    add(
        "Threshold counts reconcile to All",
        np.array_equal(pivot[["Below 0.5", "Above 0.5"]].sum(axis=1), pivot.All),
        "Below/above threshold counts sum in every year",
    )
    errors = []
    for _, g in portfolios.groupby("portfolio", sort=False):
        errors.extend(np.abs(np.diff(np.log(g.dividends)) - g.dg.to_numpy()[1:]))
    error = float(np.max(errors))
    add(
        "Portfolio dividend growth reconciles to dividend levels",
        error < 1e-8,
        f"Workbook precision tolerance 1e-8; maximum absolute log-growth difference {error:.3g}",
    )
    # Each source has a fixed real/nominal scale. Its level need not be identical across markets.
    for name, start in [
        ("Data_Netherlands_UK_1602_1812", 1629),
        ("Data_UK_1813_1870", 1813),
        ("Data_US_1871_2022", 1871),
    ]:
        d = pd.read_parquet(CLEAN / (name + ".parquet"))
        d = d[d.Year >= start]
        price_scale = d.P_real * d.CPI / d.P_nom
        div_scale = d.D_real * d.CPI / d.D_nom
        relative = float(
            max(
                np.max(abs(price_scale / price_scale.median() - 1)),
                np.max(abs(div_scale / price_scale.median() - 1)),
            )
        )
        add(
            name + " real/nominal deflation identity",
            relative < 1e-6,
            f"maximum relative scaling deviation {relative:.3g}",
        )
    fig = pd.read_csv(OUT / "figure_data/figure_3.csv")
    add(
        "Figure 3 has all computed sample points",
        len(fig) == 9
        and (fig.Source == "time").sum() == 3
        and (fig.Source == "cross").sum() == 6,
        "Three historical and six portfolio points",
    )
    return checks


def plot_validation(counts):
    """Display independently recomputed cell counts; source constants are excluded."""
    import matplotlib.pyplot as plt

    from .figures import save, theme

    theme()
    fig, ax = plt.subplots(figsize=(7, 3.8))
    x = np.arange(len(counts))
    ax.barh(
        x, counts.within_tolerance, color="#1F6F5F", label="Within published rounding"
    )
    ax.barh(
        x,
        counts.differences,
        left=counts.within_tolerance,
        color="#B5473C",
        label="Differences",
    )
    for i, row in counts.iterrows():
        ax.text(
            row.recomputed_cells + 1,
            i,
            f"{row.within_tolerance}/{row.recomputed_cells}",
            va="center",
            fontsize=9,
        )
    ax.set_yticks(x, [f"Table {n}" for n in counts.table])
    ax.invert_yaxis()
    ax.set_xlim(0, counts.recomputed_cells.max() * 1.18)
    ax.set_xlabel("Independently recomputed numeric cells")
    ax.set_title("Published-value reconciliation", loc="left", fontsize=11)
    ax.legend(loc="upper right", fontsize=8)
    fig.subplots_adjust(left=0.14, right=0.96, top=0.87, bottom=0.22)
    fig.text(
        0.14,
        0.035,
        "Tolerance: 0.0051 for two-decimal values; exact integer counts.\nTable 4’s three hard-coded smoothing values are excluded.",
        fontsize=8,
        color="#5E6462",
    )
    save(fig, "validation")


def provenance():
    """Record file hashes for each completed build without modifying upstream sources."""
    expected = json.loads((ROOT / "config/authors_package.json").read_text())["files"]
    inputs = {
        str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p): sha256(p)
        for p in sorted(RAW.iterdir())
        if p.is_file()
    }
    code = {
        str(p.relative_to(ROOT)): sha256(p)
        for p in [
            ROOT / "dodo.py",
            ROOT / "pyproject.toml",
            ROOT / "uv.lock",
            *sorted((ROOT / "src/p22").glob("*.py")),
            *sorted((ROOT / "config").glob("*.json")),
        ]
    }
    changed = [
        p.name
        for p in RAW.iterdir()
        if p.is_file() and expected.get(p.name) != sha256(p)
    ]
    outputs = {
        str(p.relative_to(OUT)): sha256(p)
        for p in sorted(OUT.rglob("*"))
        if p.is_file() and "provenance" not in p.parts
    }
    stamp = datetime.now(timezone.utc).isoformat()
    record = {
        "built_at_utc": stamp,
        "python": platform.python_version(),
        "git_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "git_dirty": bool(
            subprocess.check_output(
                ["git", "status", "--porcelain"], cwd=ROOT, text=True
            ).strip()
        ),
        "settings": settings(),
        "source_doi": "10.17632/fp6fryn7h3.1",
        "input_hashes": inputs,
        "code_and_config_hashes": code,
        "output_hashes": outputs,
        "modified_author_files": changed,
    }
    write_json(OUT / "provenance/latest.json", record)
    with (OUT / "provenance/build_history.jsonl").open("a") as f:
        f.write(json.dumps(record) + "\n")


def report():
    """Create a browsable local exhibit report, including limitations and validation."""
    parts = [
        '<!doctype html><html><head><meta charset="utf-8"><title>P22 Python replication</title><style>'
        + STYLE
        + "</style></head><body>",
        "<h1>Equity duration and predictability</h1><p>Local Python translation of the assigned empirical exhibits. Author data: Mendeley v1, DOI 10.17632/fp6fryn7h3.1. Prepared for Lauris Li.</p>",
        "<p><strong>Scope:</strong> Tables 1, 2, 4, 5, 6, 7 and Figures 1, 3. Original 2022 sample; no recent-data update or raw-stock portfolio reconstruction is claimed.</p>",
        "<p><strong>Known source limitations:</strong> Table 4’s three smoothing values are constants from MATLAB, not independent estimates. Figure 3 below is recomputed from current tables; the separate author-summary version uses the supplied frozen workbook. Figure 1 uses correct calendar endpoints rather than the MATLAB tick offset.</p>",
        "<nav>"
        + " · ".join(f'<a href="#table{n}">Table {n}</a>' for n in TABLE_INFO)
        + ' · <a href="#figures">Figures</a> · <a href="#validation">Validation</a></nav>',
    ]
    for number, (title, note) in TABLE_INFO.items():
        frame = pd.read_csv(OUT / f"tables/table_{number}.csv", index_col=0)
        parts += [
            f'<h2 id="table{number}">Table {number}. {escape(title)}</h2><div class="scroll">',
            frame.to_html(float_format=lambda x: f"{x:,.2f}", na_rep="—", border=0),
            f'</div><p class="note">{escape(note)}</p><p><a href="tables/table_{number}.csv">Full-precision CSV</a> · <a href="tables/table_{number}.tex">LaTeX table</a></p>',
        ]
    parts += [
        '<h2 id="figures">Figures</h2><img src="figures/figure_1.svg" alt="Figure 1 payout and dividend-price ratios"><img src="figures/figure_3.svg" alt="Figure 3 computed estimates">',
        '<p><a href="figures/figure_3_author_summary.svg">Compare the authors’ saved-summary Figure 3</a></p>',
        '<h2 id="validation">Validation against the paper</h2>',
    ]
    summary = pd.read_csv(OUT / "validation/summary.csv")
    parts += [
        summary.to_html(index=False, border=0),
        '<img src="figures/validation.svg" alt="Published-value comparison">',
        '<p><a href="validation/published_comparison.html">All cell comparisons</a> · <a href="validation/data_checks.json">Data checks</a> · <a href="provenance/latest.json">Build hashes</a></p>',
        "<p>Matching original estimates establishes translation fidelity, not independent validation of how the authors constructed restricted upstream data. See REPLICATION.md for implementation details and remaining work.</p></body></html>",
    ]
    OUT.joinpath("index.html").write_text("\n".join(parts))
