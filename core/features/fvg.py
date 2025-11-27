from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class FairValueGap:
    """Structured representation of a bullish or bearish FVG."""

    index: int
    gap_type: str  # 'bullish' or 'bearish'
    upper: float
    lower: float


def detect_fvgs(df: pd.DataFrame) -> List[FairValueGap]:
    """Detect bullish/bearish fair value gaps using three-bar logic."""
    highs = df["high"]
    lows = df["low"]

    bullish_mask = (highs < lows.shift(-2)).fillna(False)
    bearish_mask = (lows > highs.shift(-2)).fillna(False)

    gaps: List[FairValueGap] = []
    for idx in df.index[bullish_mask]:
        i = df.index.get_loc(idx)
        gap = FairValueGap(
            index=i + 1,
            gap_type="bullish",
            upper=float(lows.iloc[i + 2]),
            lower=float(highs.iloc[i]),
        )
        gaps.append(gap)

    for idx in df.index[bearish_mask]:
        i = df.index.get_loc(idx)
        gap = FairValueGap(
            index=i + 1,
            gap_type="bearish",
            upper=float(lows.iloc[i]),
            lower=float(highs.iloc[i + 2]),
        )
        gaps.append(gap)

    return gaps


def is_fvg_filled(price: float, fvg: FairValueGap) -> bool:
    """Return True if price has completely filled the gap."""
    if fvg.gap_type == "bullish":
        return price <= fvg.lower
    return price >= fvg.upper


def fvg_fill_ratio(price: float, fvg: FairValueGap) -> float:
    """Return ratio (0-1) describing how much of the gap has been filled."""
    gap_size = fvg.upper - fvg.lower
    if gap_size <= 0:
        return 1.0
    if fvg.gap_type == "bullish":
        filled = np.clip(fvg.upper - price, 0.0, gap_size)
    else:
        filled = np.clip(price - fvg.lower, 0.0, gap_size)
    return float(filled / gap_size)


def fvg_mid(fvg: FairValueGap) -> float:
    """Return midpoint price of the gap."""
    return (fvg.upper + fvg.lower) / 2

