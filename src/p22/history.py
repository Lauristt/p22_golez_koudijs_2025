"""Translate Tables 4/5, retaining source splice rules and the 1700 smoothing switch."""

import numpy as np
import pandas as pd

from .common import CLEAN, OUT, settings, write_json
from .econometrics import acf1, olsnw, regression, shares
from .output import SUMMARY_ROWS, predictive_rows, save_table


def segment(name, start, end, smooth=False):
    """Create one source segment before differencing to prevent splice returns."""
    frame = pd.read_parquet(CLEAN / (name + ".parquet"))
    frame["smoothed_D"] = frame.D_real.rolling(10, min_periods=10).mean()
    frame = frame[frame.Year.between(start, end)].copy()
    p, d = frame.P_real.to_numpy(), frame.D_real.to_numpy()
    years = frame.Year.to_numpy()
    if np.any(p <= 0) or np.any(d < 0):
        raise ValueError("Positive prices and nonnegative dividends are required")
    ret = (p[1:] + d[1:]) / p[:-1] - 1
    with np.errstate(divide="ignore", invalid="ignore"):
        dg = d[1:] / d[:-1] - 1
    dp = d / p
    if smooth:
        ds = frame.smoothed_D.to_numpy()
        # Growth THROUGH 1700 is smoothed; DP is smoothed only BEFORE 1700.
        mask = years[1:] <= 1700
        dg[mask] = (ds[1:] / ds[:-1] - 1)[mask]
        mask = years < 1700
        dp[mask] = (ds / p)[mask]
    if not np.all(np.isfinite(dg)) or np.any(dg <= -1) or np.any(dp <= 0):
        raise ValueError(
            "Growth and payout inputs must be positive after historical smoothing"
        )
    return {"year": years, "ret": ret, "dg": dg, "dp": dp, "dy": d[1:] / p[:-1]}


def segments():
    """Separate historical markets and the shared U.S. 1945 boundary."""
    end = settings()["baseline_end_year"]
    return [
        segment("Data_Netherlands_UK_1602_1812", 1629, 1812, True),
        segment("Data_UK_1813_1870", 1813, 1870),
        segment("Data_US_1871_2022", 1871, 1945),
        segment("Data_US_1871_2022", 1945, end),
        segment("Data_US_1871_2022", 1871, end),
    ]


def concat(items, key):
    """Stack complete segments without inventing transition observations."""
    return np.concatenate([s[key] for s in items])


def calculate():
    """Build historical summaries and predictive regressions from author inputs."""
    cfg = settings()
    early, uk, pre, post, us = segments()
    groups = [[post], [early, uk, pre], [early, uk, us]]
    labels = ["1945–2022", "1629–1945", "1629–2022"]
    # Labels reflect the configured endpoint rather than silently implying 2022.
    labels = [
        f"1945–{cfg['baseline_end_year']}",
        "1629–1945",
        f"1629–{cfg['baseline_end_year']}",
    ]
    payout = pd.read_parquet(CLEAN / "Dividends_Earnings.parquet")
    e = payout.loc[payout.Year.between(1660, 1812), "DE"].to_numpy()
    a = payout.loc[payout.Year.between(1880, 1944), "DE"].to_numpy()
    b = payout.loc[payout.Year.between(1954, cfg["baseline_end_year"]), "DE"].to_numpy()
    payouts = [b, np.r_[e, a], np.r_[e, a, b]]
    t4 = np.empty((10, 3))
    t5 = np.full((16, 3), np.nan)
    diagnostics = []
    for col, items in enumerate(groups):
        ret, dg, dp, dy = [concat(items, k) for k in ["ret", "dg", "dp", "dy"]]
        t4[:, col] = [
            np.mean(payouts[col]) * 100,
            np.log1p(ret).mean() * 100,
            np.log1p(ret).std(ddof=1) * 100,
            dy.mean() / ret.mean(),
            np.log1p(dg).mean() * 100,
            np.log1p(dg).std(ddof=1) * 100,
            dp.mean() * 100,
            dp.std(ddof=1) * 100,
            acf1(dp),
            cfg["table4_smoothing_source_constants"][col],
        ]
        predictor = np.concatenate([np.log(s["dp"][:-1]) for s in items])
        next_dp = np.concatenate([np.log(s["dp"][1:]) for s in items])
        for j, y in enumerate([np.log1p(ret), np.log1p(dg), next_dp]):
            fit = regression(y, predictor, cfg["hac_annual_lags"])
            t5[4 * j : 4 * j + 2, col] = [fit.beta[1], fit.tstat[1]]
            t5[4 * j + 3, col] = fit.r2
        # Preserve authors' full-period rho: dp_3 and dp_4 both include 1945.
        rho_dp = np.log(concat([early, uk, pre, post] if col == 2 else items, "dp"))
        t5[12:, col] = shares(t5[0, col], t5[4, col], t5[8, col], rho_dp)
        diagnostics.append(
            {
                "sample": labels[col],
                "level_observations": len(dp),
                "regression_observations": len(predictor),
                "payout_observations": len(payouts[col]),
            }
        )
    items = [early, uk, pre, post]
    xdp = np.concatenate([np.log(s["dp"][:-1]) for s in items])
    dummy = np.r_[
        np.ones(sum(len(s["ret"]) for s in items[:3])), np.zeros(len(post["ret"]))
    ]
    x = np.column_stack([np.ones(len(dummy)), dummy, xdp, xdp * dummy])
    outcomes = [
        np.log1p(concat(items, "ret")),
        np.log1p(concat(items, "dg")),
        np.concatenate([np.log(s["dp"][1:]) for s in items]),
    ]
    for j, y in enumerate(outcomes):
        t5[4 * j + 2, 1] = olsnw(y, x, cfg["hac_annual_lags"]).tstat[3]
    save_table(4, t4, SUMMARY_ROWS, labels)
    save_table(5, t5, predictive_rows("difference t-stat"), labels)
    write_json(
        OUT / "diagnostics/history.json",
        {
            "samples": diagnostics,
            "smoothing_status": "Three constants supplied in Table_4_Time_Series.m; missing upstream estimation file. Not independently reproduced.",
        },
    )
