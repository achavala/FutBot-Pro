from __future__ import annotations

from datetime import datetime

import pandas as pd
import pytest

from core.features.fvg import FairValueGap
from core.regime.engine import RegimeEngine
from core.regime.types import Bias, RegimeType, TrendDirection, VolatilityLevel


@pytest.fixture(scope="module")
def engine() -> RegimeEngine:
    return RegimeEngine(debug=True)


def test_trend_regime_detection(engine: RegimeEngine):
    signal = engine.classify_bar(
        {
            "timestamp": datetime.utcnow(),
            "adx": 35,
            "slope": 0.2,
            "r_squared": 0.8,
            "hurst": 0.6,
            "atr_pct": 1.5,
            "vwap_deviation": 1.0,
        }
    )
    assert signal.regime_type == RegimeType.TREND
    assert signal.trend_direction == TrendDirection.UP
    assert signal.bias == Bias.LONG
    assert signal.is_trending


def test_mean_reversion_regime_detection(engine: RegimeEngine):
    signal = engine.classify_bar(
        {
            "adx": 15,
            "slope": 0.01,
            "r_squared": 0.2,
            "hurst": 0.3,
            "atr_pct": 0.8,
            "vwap_deviation": 0.2,
        }
    )
    assert signal.regime_type == RegimeType.MEAN_REVERSION
    assert signal.bias in (Bias.LONG, Bias.SHORT, Bias.NEUTRAL)
    assert signal.is_mean_reversion


def test_volatility_bucket(engine: RegimeEngine):
    low = engine.classify_bar({"atr_pct": 0.5})
    medium = engine.classify_bar({"atr_pct": 1.5})
    high = engine.classify_bar({"atr_pct": 3})

    assert low.volatility_level == VolatilityLevel.LOW
    assert medium.volatility_level == VolatilityLevel.MEDIUM
    assert high.volatility_level == VolatilityLevel.HIGH
    assert high.is_high_volatility


def test_active_fvg_selection(engine: RegimeEngine):
    fvgs = [FairValueGap(index=10, gap_type="bullish", upper=102, lower=100)]
    signal = engine.classify_bar(
        {
            "adx": 10,
            "slope": 0.0,
            "r_squared": 0.1,
            "hurst": 0.4,
            "atr_pct": 1.0,
            "vwap_deviation": 0.1,
            "close": 101,
            "bar_index": 15,
            "active_fvgs": fvgs,
        }
    )
    assert signal.active_fvg is not None
    assert signal.active_fvg.gap_type == "bullish"

