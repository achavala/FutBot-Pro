from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np
import pandas as pd
from statsmodels.base.model import GenericLikelihoodModel


def hurst_exponent(series: pd.Series, min_lag: int = 2, max_lag: int = 20) -> float:
    """Estimate the Hurst exponent using a rescaled range approximation."""
    cleaned = series.dropna()
    lags = range(min_lag, max_lag)
    tau = [np.sqrt((cleaned.shift(lag) - cleaned).dropna().var()) for lag in lags]
    tau = np.array(tau)
    valid = tau > 0
    if valid.sum() < 2:
        return 0.5
    poly = np.polyfit(np.log(np.array(list(lags))[valid]), np.log(tau[valid]), 1)
    return float(poly[0]) * 2.0


def rolling_regression(series: pd.Series, window: int = 30) -> pd.DataFrame:
    """Return rolling slope and R^2 of price vs. time."""
    slopes = pd.Series(index=series.index, dtype=float)
    r2 = pd.Series(index=series.index, dtype=float)
    x = np.arange(window)

    for end in range(window, len(series) + 1):
        segment = series.iloc[end - window : end].values
        slope, intercept = np.polyfit(x, segment, 1)
        y_hat = intercept + slope * x
        ss_res = np.sum((segment - y_hat) ** 2)
        ss_tot = np.sum((segment - segment.mean()) ** 2)
        slopes.iloc[end - 1] = slope
        r2.iloc[end - 1] = 1 - ss_res / ss_tot if ss_tot else 0.0

    return pd.DataFrame({"slope": slopes, "r_squared": r2})


class _GARCH11(GenericLikelihoodModel):
    """Minimal GARCH(1,1) implementation leveraging statsmodels optimizers."""

    def loglikeobs(self, params: np.ndarray) -> np.ndarray:
        omega, alpha, beta = params
        if omega <= 0 or alpha < 0 or beta < 0 or (alpha + beta) >= 1:
            return np.full_like(self.endog, -1e6, dtype=float)

        residuals = self.endog - self.endog.mean()
        sigma2 = np.empty_like(residuals)
        sigma2[0] = residuals.var() if residuals.var() > 0 else 1e-6
        for t in range(1, residuals.size):
            sigma2[t] = omega + alpha * residuals[t - 1] ** 2 + beta * sigma2[t - 1]
        loglik = -0.5 * (np.log(2 * np.pi) + np.log(sigma2) + (residuals**2) / sigma2)
        return loglik

    def conditional_variance(self, params: np.ndarray) -> np.ndarray:
        residuals = self.endog - self.endog.mean()
        sigma2 = np.empty_like(residuals)
        sigma2[0] = residuals.var() if residuals.var() > 0 else 1e-6
        omega, alpha, beta = params
        for t in range(1, residuals.size):
            sigma2[t] = omega + alpha * residuals[t - 1] ** 2 + beta * sigma2[t - 1]
        return sigma2


def garch_volatility(series: pd.Series) -> pd.Series:
    """Fit a simple GARCH(1,1) model and return conditional volatility."""
    returns = series.pct_change().dropna()
    if len(returns) < 30:
        return pd.Series(np.nan, index=series.index)

    model = _GARCH11(returns.values)
    result = model.fit(start_params=[1e-6, 0.05, 0.9], disp=0)
    sigma2 = model.conditional_variance(result.params)
    vol = pd.Series(np.sqrt(sigma2), index=returns.index)
    return vol.reindex(series.index).ffill()


def minute_displacement(df: pd.DataFrame) -> pd.Series:
    """Return absolute displacement between open and close for each bar."""
    return (df["close"] - df["open"]).abs()


def estimate_iv_proxy(df: pd.DataFrame, window: int = 30) -> pd.Series:
    """Return blended IV proxy using Parkinson, Garman-Klass, and Rogers-Satchell estimators."""
    high = df["high"]
    low = df["low"]
    close = df["close"]
    open_ = df["open"]

    parkinson = (1 / (4 * np.log(2))) * (np.log(high / low) ** 2)
    garman_klass = (
        0.5 * (np.log(high / low) ** 2)
        - (2 * np.log(2) - 1) * (np.log(close / open_) ** 2)
    )
    rs = (
        np.log(high / close) * np.log(high / open_)
        + np.log(low / close) * np.log(low / open_)
    )
    blended = pd.concat([parkinson, garman_klass, rs], axis=1).mean(axis=1)
    return blended.rolling(window=window, min_periods=window).mean()

