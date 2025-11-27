from __future__ import annotations

import pytest

from core.risk.manager import RiskConfig, RiskManager


def test_risk_manager_initialization():
    manager = RiskManager(initial_capital=100000.0)
    assert manager.initial_capital == 100000.0
    assert manager.current_capital == 100000.0
    assert not manager.kill_switch_engaged


def test_daily_loss_limit():
    config = RiskConfig(max_daily_loss_pct=0.02)  # 2%
    manager = RiskManager(100000.0, config)
    manager.update_capital(-3000.0)  # 3% loss

    assert manager.check_daily_loss_limit()


def test_loss_streak():
    config = RiskConfig(max_loss_streak=3)
    manager = RiskManager(100000.0, config)

    manager.update_capital(-100.0)
    manager.update_capital(-100.0)
    manager.update_capital(-100.0)

    assert manager.check_loss_streak()


def test_compute_position_size():
    manager = RiskManager(100000.0)
    size = manager.compute_position_size(position_delta=1.0, price=150.0, confidence=0.8)

    assert size > 0
    assert size <= (100000.0 * 0.1) / 150.0  # Max 10% of capital


def test_can_trade():
    manager = RiskManager(100000.0)
    assert manager.can_trade(0.8)

    manager.engage_kill_switch()
    assert not manager.can_trade(0.8)


def test_kill_switch():
    manager = RiskManager(100000.0)
    assert not manager.kill_switch_engaged

    manager.engage_kill_switch()
    assert manager.kill_switch_engaged

    manager.disengage_kill_switch()
    assert not manager.kill_switch_engaged


def test_cvar_position_sizing():
    manager = RiskManager(100000.0)
    # Add some negative returns
    manager.update_capital(-500.0)
    manager.update_capital(-500.0)
    manager.update_capital(-500.0)

    base_size = 100.0
    adjusted = manager.compute_cvar_position_size(base_size)
    assert adjusted <= base_size  # Should reduce size with negative tail

