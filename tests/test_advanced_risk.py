from __future__ import annotations

import pytest

from core.regime.types import RegimeType, VolatilityLevel
from core.risk.advanced import AdvancedRiskConfig, AdvancedRiskManager


def test_advanced_risk_initialization():
    """Test advanced risk manager initialization."""
    manager = AdvancedRiskManager(initial_capital=100000.0)
    assert manager.initial_capital == 100000.0
    assert manager.current_capital == 100000.0
    assert not manager.circuit_breaker_active


def test_drawdown_calculation():
    """Test drawdown calculation."""
    manager = AdvancedRiskManager(100000.0)
    manager.update_equity(110000.0)  # Peak
    manager.update_equity(105000.0)  # Drawdown
    dd = manager.get_current_drawdown()
    assert dd > 0
    assert dd == pytest.approx(4.55, abs=0.1)  # (110k - 105k) / 110k * 100


def test_drawdown_limits():
    """Test drawdown limit checks."""
    config = AdvancedRiskConfig(max_drawdown_pct=10.0, soft_drawdown_pct=5.0)
    manager = AdvancedRiskManager(100000.0, config)
    manager.update_equity(100000.0)
    manager.update_equity(94000.0)  # 6% drawdown

    hard_stop, reason = manager.check_drawdown_limits()
    assert not hard_stop  # Below 10% hard limit
    assert "Soft" in reason  # Above 5% soft limit

    manager.update_equity(89000.0)  # 11% drawdown
    hard_stop, reason = manager.check_drawdown_limits()
    assert hard_stop  # Above 10% hard limit


def test_circuit_breaker():
    """Test circuit breaker activation."""
    config = AdvancedRiskConfig(max_losses_in_window=3, loss_window_size=5)
    manager = AdvancedRiskManager(100000.0, config)

    # Add losses
    manager.update_pnl(-100.0)
    manager.update_pnl(-100.0)
    manager.update_pnl(-100.0)

    active, reason = manager.check_circuit_breaker(0)
    assert active
    assert "Circuit breaker" in reason


def test_volatility_scaling():
    """Test volatility-based position scaling."""
    manager = AdvancedRiskManager(100000.0)
    base_size = 100.0

    # High volatility should reduce size
    scaled_high = manager.volatility_scaled_size(base_size, VolatilityLevel.HIGH, VolatilityLevel.MEDIUM)
    assert scaled_high < base_size

    # Low volatility should keep size
    scaled_low = manager.volatility_scaled_size(base_size, VolatilityLevel.LOW, VolatilityLevel.MEDIUM)
    assert scaled_low == base_size


def test_regime_aware_caps():
    """Test regime-aware position caps."""
    manager = AdvancedRiskManager(100000.0)
    trend_cap = manager.regime_aware_position_cap(RegimeType.TREND)
    mr_cap = manager.regime_aware_position_cap(RegimeType.MEAN_REVERSION)
    compression_cap = manager.regime_aware_position_cap(RegimeType.COMPRESSION)

    assert trend_cap > mr_cap
    assert compression_cap < mr_cap


def test_var_calculation():
    """Test VaR calculation."""
    import random
    manager = AdvancedRiskManager(100000.0)
    # Add some returns with variation
    equity = 100000.0
    for _ in range(50):
        equity += random.uniform(-500, 500)  # Random variation
        manager.update_equity(equity)

    var = manager.calculate_var()
    assert var >= 0


def test_advanced_position_sizing():
    """Test advanced position sizing with all controls."""
    manager = AdvancedRiskManager(100000.0)
    base_size = 1000.0
    price = 150.0

    size, reason = manager.compute_advanced_position_size(
        base_size, price, 0.8, RegimeType.TREND, VolatilityLevel.MEDIUM, 0
    )

    assert size > 0
    assert size <= base_size  # Should be reduced by various factors


def test_can_trade_advanced():
    """Test advanced can_trade check."""
    manager = AdvancedRiskManager(100000.0)

    can_trade, reason = manager.can_trade_advanced(0.8, RegimeType.TREND, VolatilityLevel.MEDIUM, 0)
    assert can_trade

    # Low confidence should fail
    can_trade, reason = manager.can_trade_advanced(0.2, RegimeType.TREND, VolatilityLevel.MEDIUM, 0)
    assert not can_trade


def test_risk_metrics():
    """Test risk metrics generation."""
    manager = AdvancedRiskManager(100000.0)
    manager.update_equity(105000.0)
    metrics = manager.get_risk_metrics()

    assert "current_drawdown_pct" in metrics
    assert "peak_equity" in metrics
    assert "circuit_breaker_active" in metrics
    assert "var_95" in metrics

