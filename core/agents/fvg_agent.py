from __future__ import annotations

from typing import List, Mapping

from core.agents.base import BaseAgent, TradeDirection, TradeIntent
from core.features.fvg import fvg_mid
from core.regime.types import Bias, RegimeSignal


class FVGAgent(BaseAgent):
    """Targets fair value gaps during imbalance regimes."""

    def __init__(self, symbol: str, config: Mapping[str, float] | None = None):
        super().__init__("fvg_agent", symbol, config)
        self.min_confidence = float(self.config.get("min_confidence", 0.5))
        self.position_size = float(self.config.get("position_size", 0.5))

    def evaluate(self, signal: RegimeSignal, market_state: Mapping[str, float]) -> List[TradeIntent]:
        fvg = signal.active_fvg
        if fvg is None or signal.confidence < self.min_confidence:
            return []

        price = float(market_state.get("close", market_state.get("price", 0.0)))
        midpoint = fvg_mid(fvg)
        if price == 0:
            return []

        if fvg.gap_type == "bullish" and price <= midpoint:
            direction = TradeDirection.LONG
        elif fvg.gap_type == "bearish" and price >= midpoint:
            direction = TradeDirection.SHORT
        else:
            return []

        bias_note = "fvg_alignment"
        metadata = {"fvg_mid": midpoint, "price": price}
        return [self._build_intent(direction, self.position_size, signal.confidence, bias_note, metadata)]

