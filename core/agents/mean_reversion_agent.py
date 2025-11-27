from __future__ import annotations

from typing import List, Mapping

from core.agents.base import BaseAgent, TradeDirection, TradeIntent
from core.regime.types import Bias, RegimeSignal


class MeanReversionAgent(BaseAgent):
    """Trades toward VWAP or FVG midpoint when regime favors mean reversion."""

    def __init__(self, symbol: str, config: Mapping[str, float] | None = None):
        super().__init__("mean_reversion_agent", symbol, config)
        self.min_confidence = float(self.config.get("min_confidence", 0.55))
        self.position_size = float(self.config.get("position_size", 0.75))

    def evaluate(self, signal: RegimeSignal, market_state: Mapping[str, float]) -> List[TradeIntent]:
        if not signal.is_mean_reversion or signal.confidence < self.min_confidence:
            return []

        if signal.bias == Bias.LONG:
            direction = TradeDirection.LONG
            reason = "mean_reversion_long_bias"
        elif signal.bias == Bias.SHORT:
            direction = TradeDirection.SHORT
            reason = "mean_reversion_short_bias"
        else:
            return []

        return [self._build_intent(direction, self.position_size, signal.confidence, reason)]

