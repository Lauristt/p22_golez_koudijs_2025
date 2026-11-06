"""Translate Table_6_7_Cross_Section.m using the authors' preconstructed portfolios."""

import numpy as np
import pandas as pd

from .common import CLEAN, OUT, settings, write_json
from .econometrics import acf1, regression, shares
from .ingest import PORTFOLIOS
from .output import PORTFOLIO_ROWS, predictive_rows, save_table


def calculate():
    """Estimate annual portfolio summaries and predictability without stock re-sorting."""
    cfg = settings()
    data = pd.read_parquet(CLEAN / "portfolios.parquet")
    data = data[data.year <= cfg["baseline_end_year"]]
    t6 = np.empty((13, 6))
    t7 = np.empty((13, 6))
    diagnostics = []
    for col, name in enumerate(PORTFOLIOS):
        d = data[data.portfolio == name].copy()
        h = cfg["rolling_years"]
        payout = (d.dividends.rolling(h).mean() / d.earnings.rolling(h).mean()).iloc[
            h - 1 :
        ]
        dp = d.dp.to_numpy()
        ret = d.ret.to_numpy()[1:]
        growth = d.dg.to_numpy()[1:]
        smooth = np.std(growth, ddof=1) / np.std(d.eg.to_numpy()[1:], ddof=1)
        t6[:, col] = [
            d.n_stocks.mean(),
            d.n_stocks.min(),
            d.n_stocks.max(),
            payout.mean() * 100,
            ret.mean() * 100,
            ret.std(ddof=1) * 100,
            1 - np.expm1(d.retx.iloc[1:]).mean() / np.expm1(ret).mean(),
            growth.mean() * 100,
            growth.std(ddof=1) * 100,
            np.exp(dp).mean() * 100,
            np.exp(dp).std(ddof=1) * 100,
            acf1(np.exp(dp)),
            smooth,
        ]
        for j, y in enumerate([ret, growth, dp[1:]]):
            fit = regression(y, dp[:-1], cfg["hac_annual_lags"])
            t7[3 * j : 3 * j + 3, col] = [fit.beta[1], fit.tstat[1], fit.r2]
        t7[9:, col] = shares(t7[0, col], t7[3, col], t7[6, col], dp)
        diagnostics.append(
            {
                "portfolio": name,
                "level_observations": len(d),
                "regression_observations": len(ret),
                "first_year": int(d.year.min()),
                "last_year": int(d.year.max()),
            }
        )
    save_table(6, t6, PORTFOLIO_ROWS, PORTFOLIOS)
    save_table(7, t7, predictive_rows(), PORTFOLIOS)
    write_json(OUT / "diagnostics/portfolios.json", diagnostics)
