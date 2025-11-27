from __future__ import annotations

import pytest

from core.policy_adaptation.adaptor import PolicyAdaptor
from core.policy_adaptation.config_manager import PolicyConfigManager
from core.policy_adaptation.evolution_rules import (
    is_change_significant,
    should_apply_cooldown,
    update_agent_weight,
    update_regime_weight,
    update_structural_weight,
    update_volatility_weight,
)
from core.policy_adaptation.stats import clamp, ema_smooth, percentage_change
from core.policy_adaptation.thresholds import AdaptationThresholds, DEFAULT_THRESHOLDS
from core.regime.types import RegimeType, VolatilityLevel
from core.reward.memory import FitnessSnapshot, RollingMemoryStore


def test_ema_smoothing():
    old = 1.0
    new = 2.0
    alpha = 0.3
    result = ema_smooth(old, new, alpha)
    assert 1.0 < result < 2.0
    assert result == old * (1 - alpha) + new * alpha


def test_clamp():
    assert clamp(0.5, 0.1, 3.0) == 0.5
    assert clamp(0.05, 0.1, 3.0) == 0.1
    assert clamp(5.0, 0.1, 3.0) == 3.0


def test_percentage_change():
    assert percentage_change(1.0, 1.1) == pytest.approx(0.1)
    assert percentage_change(1.0, 0.9) == pytest.approx(0.1)
    assert percentage_change(0.0, 1.0) == float("inf")


def test_is_change_significant():
    thresholds = DEFAULT_THRESHOLDS
    assert is_change_significant(1.0, 1.01, thresholds)  # 1% change
    assert not is_change_significant(1.0, 1.0001, thresholds)  # 0.01% change


def test_update_agent_weight_positive_fitness():
    thresholds = DEFAULT_THRESHOLDS
    fitness = FitnessSnapshot(short_term=0.5, long_term=0.3)
    current = 1.0
    new = update_agent_weight("test_agent", current, fitness, thresholds, {}, 0)
    assert new > current


def test_update_agent_weight_negative_fitness():
    thresholds = DEFAULT_THRESHOLDS
    fitness = FitnessSnapshot(short_term=-0.5, long_term=-0.3)
    current = 1.0
    new = update_agent_weight("test_agent", current, fitness, thresholds, {}, 0)
    assert new < current


def test_update_agent_weight_bounds():
    thresholds = DEFAULT_THRESHOLDS
    fitness = FitnessSnapshot(short_term=10.0, long_term=10.0)  # extreme positive
    current = 1.0
    new = update_agent_weight("test_agent", current, fitness, thresholds, {}, 0)
    assert thresholds.min_agent_weight <= new <= thresholds.max_agent_weight


def test_update_regime_weight():
    thresholds = DEFAULT_THRESHOLDS
    current = 1.2
    regime_fitness = 0.5
    new = update_regime_weight(RegimeType.TREND, current, regime_fitness, thresholds)
    assert new > current
    assert thresholds.min_regime_weight <= new <= thresholds.max_regime_weight


def test_update_volatility_weight():
    thresholds = DEFAULT_THRESHOLDS
    current = 1.0
    vol_fitness = 0.3
    new = update_volatility_weight(VolatilityLevel.HIGH, current, vol_fitness, thresholds)
    assert new > current
    assert thresholds.min_volatility_weight <= new <= thresholds.max_volatility_weight


def test_update_structural_weight_aligned():
    thresholds = DEFAULT_THRESHOLDS
    current = 1.2
    success_rate = 0.8
    new = update_structural_weight("aligned", current, success_rate, thresholds)
    assert new > current


def test_update_structural_weight_conflict():
    thresholds = DEFAULT_THRESHOLDS
    current = 0.8
    success_rate = 0.2  # low success
    new = update_structural_weight("conflict", current, success_rate, thresholds)
    assert new < current


def test_should_apply_cooldown():
    thresholds = DEFAULT_THRESHOLDS
    old = 1.0
    new = 1.2  # 20% change
    last_update = 0
    current = 5
    assert should_apply_cooldown(old, new, thresholds, last_update, current)


def test_policy_adaptor_initialization():
    memory = RollingMemoryStore()
    adaptor = PolicyAdaptor(memory)
    assert adaptor.get_agent_weight("trend_agent") > 0
    assert adaptor.get_regime_weight(RegimeType.TREND) > 0


def test_policy_adaptor_updates_weights():
    memory = RollingMemoryStore()
    adaptor = PolicyAdaptor(memory)

    # Record positive fitness
    memory.update_agent("trend_agent", 0.5)
    memory.update_agent("trend_agent", 0.6)
    memory.update_agent("trend_agent", 0.7)

    old_weight = adaptor.get_agent_weight("trend_agent")
    updates = adaptor.update_weights(bar_index=100)
    new_weight = adaptor.get_agent_weight("trend_agent")

    # Weight should increase with positive fitness
    assert new_weight >= old_weight or "agent_trend_agent" in updates


def test_policy_adaptor_regime_updates():
    memory = RollingMemoryStore()
    adaptor = PolicyAdaptor(memory)

    memory.update_regime(RegimeType.TREND, 0.5)
    memory.update_regime(RegimeType.TREND, 0.6)

    old_weight = adaptor.get_regime_weight(RegimeType.TREND)
    adaptor.update_weights(bar_index=100)
    new_weight = adaptor.get_regime_weight(RegimeType.TREND)

    assert new_weight >= old_weight


def test_policy_adaptor_volatility_updates():
    memory = RollingMemoryStore()
    adaptor = PolicyAdaptor(memory)

    memory.update_volatility(VolatilityLevel.HIGH, 0.4)
    memory.update_volatility(VolatilityLevel.HIGH, 0.5)

    old_weight = adaptor.get_volatility_weight(VolatilityLevel.HIGH)
    adaptor.update_weights(bar_index=100)
    new_weight = adaptor.get_volatility_weight(VolatilityLevel.HIGH)

    assert new_weight >= old_weight


def test_policy_adaptor_structural_tracking():
    memory = RollingMemoryStore()
    adaptor = PolicyAdaptor(memory)

    adaptor.record_structural_outcome("aligned", True)
    adaptor.record_structural_outcome("aligned", True)
    adaptor.record_structural_outcome("aligned", False)

    old_weight = adaptor.get_structure_weight("aligned")
    adaptor.update_weights(bar_index=100)
    new_weight = adaptor.get_structure_weight("aligned")

    # Should adapt based on success rate
    assert isinstance(new_weight, float)
    assert new_weight > 0


def test_policy_adaptor_freeze_flags():
    memory = RollingMemoryStore()
    adaptor = PolicyAdaptor(memory, freeze_all=True)

    memory.update_agent("trend_agent", 0.5)
    old_weight = adaptor.get_agent_weight("trend_agent")
    updates = adaptor.update_weights(bar_index=100)
    new_weight = adaptor.get_agent_weight("trend_agent")

    assert old_weight == new_weight
    assert not updates


def test_config_manager_defaults():
    manager = PolicyConfigManager()
    agent_weights, regime_weights, vol_weights, struct_weights = manager.load_weights()
    assert "trend_agent" in agent_weights
    assert RegimeType.TREND in regime_weights
    assert VolatilityLevel.LOW in vol_weights
    assert "aligned" in struct_weights


def test_config_manager_save_load(tmp_path):
    import yaml
    from pathlib import Path

    config_path = tmp_path / "test_weights.yaml"
    manager = PolicyConfigManager(config_path=config_path)

    agent_weights = {"test_agent": 1.5}
    regime_weights = {RegimeType.TREND: 1.3}
    vol_weights = {VolatilityLevel.HIGH: 1.1}
    struct_weights = {"aligned": 1.4}

    manager.save_weights(agent_weights, regime_weights, vol_weights, struct_weights)
    loaded = manager.load_weights()

    assert loaded[0]["test_agent"] == 1.5
    assert loaded[1][RegimeType.TREND] == 1.3
    assert loaded[2][VolatilityLevel.HIGH] == 1.1
    assert loaded[3]["aligned"] == 1.4

