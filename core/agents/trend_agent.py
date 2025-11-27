from __future__ import annotations

from typing import List, Mapping

from core.agents.base import BaseAgent, TradeDirection, TradeIntent
from core.regime.types import Bias, RegimeSignal, TrendDirection


class TrendAgent(BaseAgent):
    """Follows directional moves when regime confirms trend conditions."""

    def __init__(self, symbol: str, config: Mapping[str, float] | None = None):
        super().__init__("trend_agent", symbol, config)
        self.min_confidence = float(self.config.get("min_confidence", 0.6))
        self.position_size = float(self.config.get("position_size", 1.0))

    def evaluate(self, signal: RegimeSignal, market_state: Mapping[str, float]) -> List[TradeIntent]:
        if not signal.is_trending or signal.confidence < self.min_confidence:
            return []
        if signal.bias == Bias.NEUTRAL:
            return []
        direction = TradeDirection.LONG if signal.trend_direction == TrendDirection.UP else TradeDirection.SHORT
        intent = self._build_intent(direction, self.position_size, signal.confidence, "trend_regime_alignment")
        return [intent]

