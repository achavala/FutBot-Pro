from __future__ import annotations

from dataclasses import dataclass

from core.policy.types import FinalTradeIntent
from core.regime.types import Bias, RegimeSignal, RegimeType, TrendDirection, VolatilityLevel
from core.reward.attribution import AgentContribution
from core.reward.memory import RollingMemoryStore
from core.reward.tracker import RewardTracker


def build_signal(regime: RegimeType = RegimeType.TREND, bias: Bias = Bias.LONG) -> RegimeSignal:
    return RegimeSignal(
        timestamp=None,
        trend_direction=TrendDirection.UP if bias != Bias.SHORT else TrendDirection.DOWN,
        volatility_level=VolatilityLevel.MEDIUM,
        regime_type=regime,
        bias=bias,
        confidence=0.8,
        active_fvg=None,
        metrics={},
        is_valid=True,
    )


def build_intent(position_delta: float = 1.0, confidence: float = 0.8, primary_agent: str = "trend_agent") -> FinalTradeIntent:
    return FinalTradeIntent(
        position_delta=position_delta,
        confidence=confidence,
        primary_agent=primary_agent,
        contributing_agents=[primary_agent, "mean_reversion_agent"],
        reason="test",
        is_valid=True,
    )


def test_reward_tracker_positive_outcome():
    memory = RollingMemoryStore()
    tracker = RewardTracker(memory_store=memory)
    signal = build_signal()
    intent = build_intent()
    contributions = [
        AgentContribution(name="trend_agent", weight=0.7),
        AgentContribution(name="mean_reversion_agent", weight=0.3),
    ]

    allocation = tracker.update(intent, next_return=0.01, signal=signal, contributions=contributions)

    assert allocation["trend_agent"] > 0
    assert memory.get_agent_fitness("trend_agent").short_term > 0
    assert memory.get_regime_fitness(RegimeType.TREND) >= 0


def test_reward_tracker_penalizes_wrong_direction():
    tracker = RewardTracker()
    signal = build_signal(bias=Bias.LONG)
    intent = build_intent(position_delta=-1.0)
    allocation = tracker.update(intent, next_return=0.01, signal=signal, contributions=None)
    total_reward = sum(allocation.values())
    assert total_reward < 0


def test_memory_volatility_bias():
    memory = RollingMemoryStore()
    tracker = RewardTracker(memory_store=memory)
    signal = build_signal()
    intent = build_intent()
    tracker.update(intent, next_return=0.005, signal=signal, contributions=None)
    bias_value = memory.get_volatility_bias(VolatilityLevel.MEDIUM)
    assert bias_value != 0

