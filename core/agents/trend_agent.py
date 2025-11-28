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
        # AGGRESSIVE MODE: Generate trades even with low/zero confidence
        # Use price action signals when confidence is low
        price = market_state.get("close", market_state.get("price", 0.0))
        ema_9 = market_state.get("ema_9", price)
        ema_21 = market_state.get("ema_21", price)
        
        # If we have price data, generate a signal based on simple price action
        if price > 0 and ema_9 > 0 and ema_21 > 0:
            # Simple trend following: if price > EMA9 > EMA21, go long
            if price > ema_9 and ema_9 > ema_21:
                # Use minimum confidence if signal confidence is too low
                effective_confidence = max(0.1, signal.confidence) if signal.confidence > 0 else 0.1
                intent = self._build_intent(TradeDirection.LONG, self.position_size, effective_confidence, "price_action_long")
                return [intent]
            elif price < ema_9 and ema_9 < ema_21:
                effective_confidence = max(0.1, signal.confidence) if signal.confidence > 0 else 0.1
                intent = self._build_intent(TradeDirection.SHORT, self.position_size, effective_confidence, "price_action_short")
                return [intent]
        
        # Original logic for high confidence signals
        if signal.is_trending and signal.confidence >= self.min_confidence:
            if signal.bias == Bias.NEUTRAL:
                return []
            direction = TradeDirection.LONG if signal.trend_direction == TrendDirection.UP else TradeDirection.SHORT
            intent = self._build_intent(direction, self.position_size, signal.confidence, "trend_regime_alignment")
            return [intent]
        
        return []

