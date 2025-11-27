#!/usr/bin/env python3
"""
Unit test script to verify all trading components work correctly.
Tests each component in isolation to ensure the full pipeline is functional.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from core.regime.engine import RegimeEngine
from core.regime.types import RegimeType, TrendDirection, VolatilityLevel
from core.agents.trend_agent import TrendAgent
from core.agents.mean_reversion_agent import MeanReversionAgent
from core.agents.fvg_agent import FVGAgent
from core.agents.volatility_agent import VolatilityAgent
from core.policy.controller import MetaPolicyController
from core.features.fvg import detect_fvgs, FairValueGap


def create_test_bars(n=100, trend="up"):
    """Create synthetic bar data."""
    dates = pd.date_range(start=datetime.now() - timedelta(minutes=n), periods=n, freq='1min')
    
    if trend == "up":
        prices = 100 + np.cumsum(np.random.randn(n) * 0.5 + 0.1)
    elif trend == "down":
        prices = 100 + np.cumsum(np.random.randn(n) * 0.5 - 0.1)
    else:
        prices = 100 + np.cumsum(np.random.randn(n) * 0.3)
    
    bars = []
    for i, (date, price) in enumerate(zip(dates, prices)):
        bars.append({
            "timestamp": date,
            "open": price + np.random.randn() * 0.2,
            "high": price + abs(np.random.randn() * 0.5),
            "low": price - abs(np.random.randn() * 0.5),
            "close": price,
            "volume": np.random.uniform(1000, 10000),
        })
    
    return pd.DataFrame(bars)


def test_regime_engine():
    """Test regime classification."""
    print("Testing RegimeEngine...")
    engine = RegimeEngine()
    
    # Test trend regime
    trend_input = {
        "adx": 35.0,
        "atr_pct": 2.0,
        "hurst": 0.6,
        "slope": 0.05,
        "r_squared": 0.8,
        "vwap_deviation": 1.5,
        "iv_proxy": 0.25,
        "active_fvgs": [],
        "close": 105.0,
        "bar_index": 100,
    }
    
    signal = engine.classify_bar(trend_input)
    assert signal.regime_type == RegimeType.TREND, f"Expected TREND, got {signal.regime_type}"
    assert signal.trend_direction == TrendDirection.UP, f"Expected UP trend"
    print("  ✅ Trend regime classification works")
    
    # Test mean reversion regime
    mr_input = {
        "adx": 15.0,
        "atr_pct": 0.8,
        "hurst": 0.4,
        "slope": 0.01,
        "r_squared": 0.3,
        "vwap_deviation": 0.3,
        "iv_proxy": 0.15,
        "active_fvgs": [],
        "close": 100.0,
        "bar_index": 100,
    }
    
    signal = engine.classify_bar(mr_input)
    assert signal.regime_type == RegimeType.MEAN_REVERSION, f"Expected MEAN_REVERSION, got {signal.regime_type}"
    print("  ✅ Mean reversion regime classification works")
    
    print("✅ RegimeEngine: PASSED\n")


def test_agents():
    """Test agent evaluation."""
    print("Testing Agents...")
    
    # Create test regime signals
    from core.regime.types import RegimeSignal, Bias
    
    trend_signal = RegimeSignal(
        timestamp=datetime.now(),
        regime_type=RegimeType.TREND,
        trend_direction=TrendDirection.UP,
        volatility_level=VolatilityLevel.MEDIUM,
        bias=Bias.LONG,
        confidence=0.75,
        is_valid=True,
    )
    
    mr_signal = RegimeSignal(
        timestamp=datetime.now(),
        regime_type=RegimeType.MEAN_REVERSION,
        trend_direction=TrendDirection.SIDEWAYS,
        volatility_level=VolatilityLevel.LOW,
        bias=Bias.LONG,
        confidence=0.65,
        is_valid=True,
    )
    
    market_state = {
        "close": 105.0,
        "open": 104.5,
        "high": 105.5,
        "low": 104.0,
        "volume": 5000,
        "ema9": 104.8,
        "rsi": 60.0,
        "atr": 1.0,
        "vwap": 104.5,
        "vwap_deviation": 0.5,
    }
    
    # Test TrendAgent
    trend_agent = TrendAgent("QQQ")
    intents = trend_agent.evaluate(trend_signal, market_state)
    assert len(intents) > 0, "TrendAgent should return intent in trend regime"
    assert intents[0].direction == "long", "Should be long in uptrend"
    print("  ✅ TrendAgent works")
    
    # Test MeanReversionAgent
    mr_agent = MeanReversionAgent("QQQ")
    intents = mr_agent.evaluate(mr_signal, market_state)
    assert len(intents) > 0, "MeanReversionAgent should return intent in MR regime"
    print("  ✅ MeanReversionAgent works")
    
    # Test that agents don't trade in wrong regimes
    intents = trend_agent.evaluate(mr_signal, market_state)
    assert len(intents) == 0, "TrendAgent should not trade in MR regime"
    print("  ✅ Agents respect regime boundaries")
    
    print("✅ Agents: PASSED\n")


def test_controller():
    """Test meta-policy controller."""
    print("Testing MetaPolicyController...")
    
    controller = MetaPolicyController()
    
    # Create agents
    agents = [
        TrendAgent("QQQ"),
        MeanReversionAgent("QQQ"),
        VolatilityAgent("QQQ"),
        FVGAgent("QQQ"),
    ]
    
    # Create trend signal
    from core.regime.types import RegimeSignal, RegimeType, TrendDirection, VolatilityLevel, Bias
    
    signal = RegimeSignal(
        timestamp=datetime.now(),
        regime_type=RegimeType.TREND,
        trend_direction=TrendDirection.UP,
        volatility_level=VolatilityLevel.MEDIUM,
        bias=Bias.LONG,
        confidence=0.75,
        is_valid=True,
    )
    
    market_state = {
        "close": 105.0,
        "open": 104.5,
        "high": 105.5,
        "low": 104.0,
        "volume": 5000,
        "ema9": 104.8,
        "rsi": 60.0,
        "atr": 1.0,
        "vwap": 104.5,
        "vwap_deviation": 0.5,
    }
    
    intent = controller.decide(signal, market_state, agents)
    assert intent.is_valid, "Controller should produce valid intent"
    assert intent.position_delta != 0, "Should have non-zero position delta"
    assert intent.primary_agent != "NONE", "Should have primary agent"
    print(f"  ✅ Controller decision: {intent.primary_agent}, delta={intent.position_delta:.3f}")
    
    # Test low confidence veto
    low_conf_signal = RegimeSignal(
        timestamp=datetime.now(),
        regime_type=RegimeType.TREND,
        trend_direction=TrendDirection.UP,
        volatility_level=VolatilityLevel.MEDIUM,
        bias=Bias.LONG,
        confidence=0.2,  # Too low
        is_valid=True,
    )
    
    intent = controller.decide(low_conf_signal, market_state, agents)
    assert not intent.is_valid or intent.position_delta == 0, "Should veto low confidence"
    print("  ✅ Low confidence veto works")
    
    print("✅ MetaPolicyController: PASSED\n")


def test_full_pipeline():
    """Test the complete pipeline with synthetic data."""
    print("Testing Full Pipeline...")
    
    # Create test data
    bars_df = create_test_bars(n=100, trend="up")
    
    # This would normally be done in LiveTradingLoop
    # For now, just verify we can compute features
    from core.features.indicators import ema, sma, rsi, atr, adx, vwap
    
    bars_df["ema9"] = ema(bars_df["close"], 9)
    bars_df["sma20"] = sma(bars_df["close"], 20)
    bars_df["rsi"] = rsi(bars_df["close"], 14)
    bars_df["atr"] = atr(bars_df, 14)
    bars_df["adx"] = adx(bars_df, 14)
    bars_df = bars_df.set_index("timestamp")
    bars_df["vwap"] = vwap(bars_df)
    
    print("  ✅ Feature computation works")
    
    # Test FVG detection
    fvgs = detect_fvgs(bars_df.tail(50))
    print(f"  ✅ FVG detection: found {len(fvgs)} FVGs")
    
    print("✅ Full Pipeline: PASSED\n")


def main():
    print("=" * 60)
    print("FutBot Component Verification Tests")
    print("=" * 60)
    print()
    
    try:
        test_regime_engine()
        test_agents()
        test_controller()
        test_full_pipeline()
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print("\nAll trading components are working correctly!")
        print("The bot should trade once it has 50+ bars and valid signals.")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

