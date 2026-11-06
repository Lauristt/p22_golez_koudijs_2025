"""Validate the translated estimator against a separate implementation."""

import numpy as np
import pytest
import statsmodels.api as sm

from p22.econometrics import olsnw, shares


@pytest.mark.parametrize("lags", [0, 1, 12])
def test_hac_matches_statsmodels(lags):
    rng = np.random.default_rng(2025)
    x = np.column_stack([np.ones(160), rng.normal(size=(160, 2))])
    errors = rng.normal(size=160)
    errors[1:] += 0.4 * errors[:-1]
    y = x @ np.array([0.1, 0.4, -0.2]) + errors
    ours = olsnw(y, x, lags)
    independent = sm.OLS(y, x).fit(
        cov_type="HAC", cov_kwds={"maxlags": lags, "use_correction": False}
    )
    np.testing.assert_allclose(ours.beta, independent.params, rtol=1e-12)
    np.testing.assert_allclose(ours.stderr, independent.bse, rtol=1e-12)
    np.testing.assert_allclose(ours.tstat, independent.tvalues, rtol=1e-12)
    assert ours.r2 == pytest.approx(independent.rsquared)
    ordinary = olsnw(y, x, lags, hac=False)
    np.testing.assert_allclose(ordinary.stderr, sm.OLS(y, x).fit().bse, rtol=1e-12)


def test_nonfinite_and_rank_deficient_inputs_are_rejected():
    with pytest.raises(ValueError, match="rank"):
        olsnw(np.arange(20), np.ones((20, 2)))
    with pytest.raises(ValueError, match="nonfinite"):
        olsnw(np.r_[np.nan, np.ones(19)], np.ones((20, 1)))


def test_shares_do_not_clip_over_one_or_negative_values():
    result = shares(0.5, 0.1, 0.9, np.full(30, -3.0))
    assert result[0] > 1 and result[2] < 0
    assert result[0] + result[3] == pytest.approx(1)
    assert result[1] + result[2] == pytest.approx(1)
