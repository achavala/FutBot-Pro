from __future__ import annotations

from typing import List, Mapping, Optional

import pytest

from core.agents.base import BaseAgent, TradeDirection, TradeIntent
from core.policy.controller import ControllerConfig, MetaPolicyController
from core.policy.types import FinalTradeIntent
from core.regime.types import Bias, RegimeSignal, RegimeType, TrendDirection, VolatilityLevel


class DummyAgent(BaseAgent):
    def __init__(self, name: str, symbol: str, responses: List[Mapping[str, object]]):
        super().__init__(name, symbol, config=None)
        self.responses = responses

    def evaluate(self, signal: RegimeSignal, market_state: Mapping[str, float]) -> List[TradeIntent]:
        intents: List[TradeIntent] = []
        for resp in self.responses:
            intent = self._build_intent(
                direction=resp.get("direction", TradeDirection.LONG),
                size=float(resp.get("size", 1.0)),
                confidence=float(resp.get("confidence", 0.5)),
                reason=str(resp.get("reason", "test")),
            )
            intents.append(intent)
        return intents


def base_signal(regime: RegimeType, bias: Bias, volatility: VolatilityLevel) -> RegimeSignal:
    return RegimeSignal(
        timestamp=None,
        trend_direction=TrendDirection.UP if bias == Bias.LONG else TrendDirection.DOWN,
        volatility_level=volatility,
        regime_type=regime,
        bias=bias,
        confidence=0.8,
        active_fvg=None,
        metrics={},
        is_valid=True,
    )


def test_controller_selects_trend_intent():
    signal = base_signal(RegimeType.TREND, Bias.LONG, VolatilityLevel.MEDIUM)
    trend_agent = DummyAgent(
        "trend_agent",
        "QQQ",
        [{"direction": TradeDirection.LONG, "size": 1.0, "confidence": 0.8, "reason": "trend_follow"}],
    )
    mr_agent = DummyAgent(
        "mean_reversion_agent",
        "QQQ",
        [{"direction": TradeDirection.SHORT, "size": 1.0, "confidence": 0.7, "reason": "fade"}],
    )
    controller = MetaPolicyController()
    result = controller.decide(signal, {"close": 100}, [trend_agent, mr_agent])
    assert isinstance(result, FinalTradeIntent)
    assert result.is_valid
    assert result.position_delta > 0
    assert result.primary_agent == "trend_agent"


def test_controller_returns_empty_when_no_valid_intents():
    signal = base_signal(RegimeType.MEAN_REVERSION, Bias.NEUTRAL, VolatilityLevel.HIGH)
    mr_agent = DummyAgent(
        "mean_reversion_agent",
        "QQQ",
        [{"direction": TradeDirection.LONG, "size": 1.0, "confidence": 0.6}],
    )
    controller = MetaPolicyController()
    result = controller.decide(signal, {"close": 100}, [mr_agent])
    assert not result.is_valid
    assert result.position_delta == 0


def test_controller_blends_close_intents():
    signal = base_signal(RegimeType.TREND, Bias.LONG, VolatilityLevel.MEDIUM)
    trend_agent = DummyAgent(
        "trend_agent",
        "QQQ",
        [{"direction": TradeDirection.LONG, "size": 1.0, "confidence": 0.8}],
    )
    vol_agent = DummyAgent(
        "volatility_agent",
        "QQQ",
        [{"direction": TradeDirection.LONG, "size": 0.5, "confidence": 0.79}],
    )
    controller = MetaPolicyController(config=ControllerConfig(blend_threshold_ratio=0.05))
    result = controller.decide(signal, {"close": 100}, [trend_agent, vol_agent])
    assert result.is_valid
    assert len(result.contributing_agents) >= 1
    assert result.position_delta > 0

