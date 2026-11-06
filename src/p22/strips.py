"""Translate Table_1_2_Dividend_Strip.m, preserving dates, horizons and HAC conventions."""

import numpy as np
import pandas as pd

from .common import CLEAN, OUT, settings, write_json
from .econometrics import regression, shares
from .output import predictive_rows, save_table


def calculate():
    """Build Tables 1 and 2 from the cleaned monthly source."""
    cfg = settings()
    data = pd.read_parquet(CLEAN / "strips.parquet")
    data = data[data.Date.dt.year <= cfg["baseline_end_year"]].iloc[
        : cfg["baseline_strip_months"]
    ]
    if len(data) < 25:
        raise ValueError("At least 25 months required for overlapping regressions")
    inf = np.log1p(data["Inflation"].to_numpy()[1:])
    dividend = data["Div_a"].to_numpy()
    ret = np.log1p(data["SP_ret"].to_numpy()[1:]) - inf
    strip = np.log1p(data["Div_strip_ret"].to_numpy()[1:]) - inf
    growth = np.diff(np.log(dividend)) - inf
    h = 12
    # MATLAB filter(...)(h:end), i.e. complete trailing 12-month sums.
    annual = [np.convolve(x, np.ones(h), "valid") for x in [ret, strip, growth]]
    dp_market = np.log(dividend / data["SP_500"].to_numpy())
    dp_strip = np.log(dividend / data["Div_strip_18m"].to_numpy())
    table1 = np.array(
        [
            [np.mean(annual[0]) * 100, np.mean(annual[1]) * 100],
            [np.std(annual[0], ddof=1) * 100, np.std(annual[1], ddof=1) * 100],
            [np.mean(annual[2]) * 100, np.nan],
            [np.std(annual[2], ddof=1) * 100, np.nan],
            [np.mean(np.exp(dp_market)) * 100, np.mean(np.exp(dp_strip)) * 100],
            [
                np.std(np.exp(dp_market), ddof=1) * 100,
                np.std(np.exp(dp_strip), ddof=1) * 100,
            ],
        ]
    )
    save_table(
        1,
        table1,
        [
            "Return mean (%)",
            "Return SD (%)",
            "Dividend growth mean (%)",
            "Dividend growth SD (%)",
            "Dividend-price mean (%)",
            "Dividend-price SD (%)",
        ],
        ["Market", "Dividend strips"],
    )
    table2 = np.full((16, 2), np.nan)
    n = len(annual[0])
    for col, dp in enumerate([dp_market, dp_strip]):
        predictor = dp[:n]
        outcomes = [annual[col], annual[2]] + ([dp_market[h:]] if col == 0 else [])
        for j, y in enumerate(outcomes):
            fit = regression(y, predictor, cfg["hac_monthly_lags"])
            non = np.mean(
                [
                    regression(y[i::h], predictor[i::h], cfg["hac_annual_lags"]).tstat[
                        1
                    ]
                    for i in range(h)
                ]
            )
            table2[4 * j : 4 * j + 4, col] = [fit.beta[1], fit.tstat[1], non, fit.r2]
    table2[12:, 0] = shares(table2[0, 0], table2[4, 0], table2[8, 0], dp_market)
    er, edg = table2[0, 1], -table2[4, 1]
    table2[12:, 1] = [er, 1 - edg, edg, 1 - er]
    save_table(
        2,
        table2,
        predictive_rows("t-stat (non-overlap)"),
        ["Market", "Dividend strips"],
    )
    write_json(
        OUT / "diagnostics/strips.json",
        {
            "monthly_levels": len(data),
            "overlapping_12_month_outcomes": n,
            "first_month": str(data.Date.iloc[0].date()),
            "last_month": str(data.Date.iloc[-1].date()),
            "non_overlap_hac_lags": cfg["hac_annual_lags"],
        },
    )
