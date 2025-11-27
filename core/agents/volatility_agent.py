from __future__ import annotations

from typing import List, Mapping

from core.agents.base import BaseAgent, TradeDirection, TradeIntent
from core.regime.types import Bias, RegimeSignal, VolatilityLevel


class VolatilityAgent(BaseAgent):
    """Seeks breakout or volatility expansion opportunities."""

    def __init__(self, symbol: str, config: Mapping[str, float] | None = None):
        super().__init__("volatility_agent", symbol, config)
        self.min_confidence = float(self.config.get("min_confidence", 0.5))
        self.position_size = float(self.config.get("position_size", 0.5))

    def evaluate(self, signal: RegimeSignal, market_state: Mapping[str, float]) -> List[TradeIntent]:
        if signal.volatility_level != VolatilityLevel.HIGH or signal.confidence < self.min_confidence:
            return []

        direction = TradeDirection.LONG if signal.bias == Bias.LONG else TradeDirection.SHORT
        if direction == TradeDirection.FLAT:
            direction = TradeDirection.LONG

        reason = "volatility_expansion"
        return [self._build_intent(direction, self.position_size, signal.confidence, reason)]

