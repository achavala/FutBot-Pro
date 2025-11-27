from __future__ import annotations

from typing import Iterable, Sequence

import numpy as np


def cumulative_pnl(returns: Sequence[float]) -> float:
    return float(np.sum(returns))


def sharpe_ratio(returns: Sequence[float], risk_free_rate: float = 0.0) -> float:
    if not returns:
        return 0.0
    arr = np.array(returns)
    excess = arr - risk_free_rate
    std = arr.std(ddof=1)
    if std == 0:
        return 0.0
    return float(excess.mean() / std * np.sqrt(252))


def max_drawdown(equity_curve: Sequence[float]) -> float:
    if not equity_curve:
        return 0.0
    arr = np.array(equity_curve)
    peaks = np.maximum.accumulate(arr)
    drawdowns = (arr - peaks) / peaks
    return float(drawdowns.min())

