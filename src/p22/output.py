"""Export full-precision numeric tables and readable HTML/LaTeX versions."""

from html import escape

import pandas as pd

from .common import OUT

TABLE_INFO = {
    1: (
        "Market and dividend strips: summary statistics",
        "January 1996–December 2022. Real log 12-month returns and growth; monthly observations. Standard deviations use n−1. Dividend-price ratios are levels in percent.",
    ),
    2: (
        "Market and dividend strips: predictability",
        "12-month outcomes, monthly observations. HAC t-statistics use 12 lags without a small-sample correction. Non-overlapping t-statistics average 12 offset regressions, each using one HAC lag, as in the supplied code. Blank cells are not applicable.",
    ),
    4: (
        "Historical market: summary statistics",
        "Real annual series. Payout coverage is incomplete before 1945. Smoothing* is copied from constants in the authors’ script, whose separate estimation file is not supplied; it is NOT independently recomputed.",
    ),
    5: (
        "Historical market: predictability",
        "Annual OLS with one-lag Newey-West standard errors. Differences are prewar interaction t-statistics. Geographic splice transitions are excluded. Full-sample rho follows the original script, including the duplicated 1945 level.",
    ),
    6: (
        "Payout portfolios: summary statistics",
        "1945–2022 author-provided portfolios; 77 annual outcomes. Ten-year trailing payout; value-weighting and stock selection were performed upstream by the authors. This pipeline does not reconstruct the raw CRSP/Compustat stock panel.",
    ),
    7: (
        "Payout portfolios: predictability",
        "Annual OLS with one-lag Newey-West standard errors, no finite-sample correction. ER/EDG are direct and implied decomposition shares, not R-squared. Negative estimates and values above one are retained.",
    ),
}
STYLE = """body{font:16px/1.5 Arial,sans-serif;color:#171717;max-width:1100px;margin:40px auto;padding:0 24px;background:white}h1{font-size:28px;font-weight:600}h2{font-size:21px;margin-top:42px}table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;font-size:14px;border-top:1px solid #333;border-bottom:1px solid #333}th,td{padding:7px 10px;text-align:right;border:0}thead th{border-bottom:1px solid #999}th:first-child{text-align:left}tbody tr:nth-child(4n+1){border-top:1px solid #e4e7e5}p.note{font-size:13px;color:#53605b}img{max-width:100%;height:auto}a{color:#1f6f5f}.scroll{overflow:auto}"""


def save_table(number, values, rows, columns):
    """Save numbers unrounded; formatting never feeds back into calculations."""
    target = OUT / "tables"
    target.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(values, index=rows, columns=columns)
    frame.index.name = "Statistic"
    frame.to_csv(target / f"table_{number}.csv", float_format="%.15g")
    title, note = TABLE_INFO[number]
    html = frame.to_html(float_format=lambda x: f"{x:,.2f}", na_rep="—", border=0)
    (target / f"table_{number}.html").write_text(
        f'<!doctype html><html><head><meta charset="utf-8"><title>Table {number}</title><style>{STYLE}</style></head><body><h1>Table {number}. {escape(title)}</h1><div class="scroll">{html}</div><p class="note">{escape(note)}</p><p class="note">Source: Golez and Koudijs (2025), Mendeley v1; Python translation by Lauris Li.</p></body></html>'
    )
    tex = frame.to_latex(
        float_format="%.2f",
        na_rep="--",
        escape=True,
        column_format="l" + "r" * len(columns),
        caption=f"Table {number}: {title}.",
        label=f"tab:replication_{number}",
    )
    (target / f"table_{number}.tex").write_text(
        "% Generated; requires booktabs.\n% " + note + "\n" + tex
    )
    return frame


SUMMARY_ROWS = [
    "Payout (%)",
    "Return mean (%)",
    "Return SD (%)",
    "DY/RET",
    "Dividend growth mean (%)",
    "Dividend growth SD (%)",
    "Dividend-price mean (%)",
    "Dividend-price SD (%)",
    "Dividend-price AR(1)",
    "Smoothing*",
]
PORTFOLIO_ROWS = [
    "Number of stocks: mean",
    "Number of stocks: min",
    "Number of stocks: max",
    "Payout (%)",
    "Return mean (%)",
    "Return SD (%)",
    "DY/RET",
    "Dividend growth mean (%)",
    "Dividend growth SD (%)",
    "Dividend-price mean (%)",
    "Dividend-price SD (%)",
    "Dividend-price AR(1)",
    "Smoothing",
]
SHARE_ROWS = ["ER", "ER (implied)", "EDG", "EDG (implied)"]


def predictive_rows(extra=None):
    """Name regression blocks in original table order."""
    rows = []
    for outcome in ["Return", "Dividend growth", "Dividend-price"]:
        rows += [outcome + " slope", outcome + " t-stat (NW)"]
        if extra:
            rows.append(outcome + " " + extra)
        rows.append(outcome + " R-squared")
    return rows + SHARE_ROWS
