"""Translate olsnw.m: OLS and Bartlett Newey-West, without small-sample HAC correction."""

from dataclasses import dataclass

import numpy as np


@dataclass
class Regression:
    """Numerical regression outputs with explicit observation count."""

    beta: np.ndarray
    stderr: np.ndarray
    tstat: np.ndarray
    r2: float
    residual: np.ndarray
    nobs: int


def olsnw(y, x, lags=1, hac=True):
    """Match authors' covariance convention; require finite full-rank aligned data."""
    y, x = np.asarray(y, dtype=float), np.asarray(x, dtype=float)
    if y.ndim != 1 or x.ndim != 2 or len(y) != len(x):
        raise ValueError("Regression dimensions do not match")
    n, k = x.shape
    if not np.isfinite(y).all() or not np.isfinite(x).all():
        raise ValueError("Regression inputs contain missing/nonfinite values")
    if n <= k or np.linalg.matrix_rank(x) < k or not 0 <= lags < n:
        raise ValueError(
            "Insufficient observations, invalid lags or rank-deficient design"
        )
    bread = np.linalg.inv(x.T @ x)
    beta = np.linalg.lstsq(x, y, rcond=None)[0]
    error = y - x @ beta
    if hac:
        scores = x * error[:, None]
        meat = scores.T @ scores
        for lag in range(1, lags + 1):
            gamma = scores[lag:].T @ scores[:-lag]
            meat += (1 - lag / (lags + 1)) * (gamma + gamma.T)
        variance = bread @ meat @ bread
    else:
        variance = bread * (error @ error) / (n - k)
    stderr = np.sqrt(np.diag(variance))
    return Regression(
        beta,
        stderr,
        beta / stderr,
        float(1 - (error @ error) / np.sum((y - y.mean()) ** 2)),
        error,
        n,
    )


def regression(y, predictor, lags=1):
    """Fit an intercept and the single predictive regressor."""
    return olsnw(y, np.column_stack([np.ones(len(predictor)), predictor]), lags)


def acf1(x):
    """MATLAB autocorr lag one: centered lag product divided by full sum of squares."""
    centered = np.asarray(x, dtype=float) - np.mean(x)
    return float(centered[1:] @ centered[:-1] / (centered @ centered))


def shares(return_beta, growth_beta, dp_beta, dp):
    """Return ER, implied ER, EDG and implied EDG in the authors' row order."""
    rho = 1 / (1 + np.exp(np.mean(dp)))
    denominator = 1 - rho * dp_beta
    er, edg = return_beta / denominator, -growth_beta / denominator
    return np.array([er, 1 - edg, edg, 1 - er])
