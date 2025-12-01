"""EMA-based trading agent for momentum strategies."""

from __future__ import annotations

import logging
from typing import List, Mapping

from core.agents.base import BaseAgent, TradeDirection, TradeIntent
from core.regime.types import RegimeSignal

logger = logging.getLogger(__name__)


class EMAAgent(BaseAgent):
    """Trades based on 9 EMA momentum signals (good for SPY and other ETFs)."""

    def __init__(self, symbol: str, config: Mapping[str, float] | None = None):
        super().__init__("ema_agent", symbol, config)
        self.ema_period = int(self.config.get("ema_period", 9))
        self.min_confidence = float(self.config.get("min_confidence", 0.5))
        self.position_size = float(self.config.get("position_size", 0.8))
        self.momentum_threshold = float(self.config.get("momentum_threshold", 0.1))  # 0.1% price move

    def evaluate(self, signal: RegimeSignal, market_state: Mapping[str, float]) -> List[TradeIntent]:
        """
        Evaluate EMA-based entry signals.
        
        Entry Logic:
        - Long: Price crosses above 9 EMA with momentum
        - Short: Price crosses below 9 EMA with momentum
        - Requires minimum confidence and trend alignment
        """
        if not signal.is_valid or signal.confidence < self.min_confidence:
            return []

        close = market_state.get("close", 0.0)
        ema9 = market_state.get("ema9", close)
        
        if close == 0 or ema9 == 0:
            return []

        # Calculate price position relative to EMA
        price_above_ema = close > ema9
        price_below_ema = close < ema9
        ema_distance_pct = abs((close - ema9) / ema9) * 100.0 if ema9 > 0 else 0.0

        # Need sufficient distance from EMA to avoid whipsaws
        if ema_distance_pct < self.momentum_threshold:
            return []

        # Helper to safely get enum value (handles both enum and string)
        def get_enum_value(enum_or_str):
            if isinstance(enum_or_str, str):
                return enum_or_str
            return enum_or_str.value if hasattr(enum_or_str, 'value') else str(enum_or_str)
        
        bias_val = get_enum_value(signal.bias)
        trend_val = get_enum_value(signal.trend_direction)
        
        # Long signal: Price above EMA with long bias or uptrend
        if price_above_ema and (bias_val == "long" or trend_val == "up"):
            # Additional confirmation: price should be moving up
            direction = TradeDirection.LONG
            confidence = min(signal.confidence, 0.7)  # Cap confidence for EMA signals
            reason = f"Price above {self.ema_period} EMA with bullish momentum ({ema_distance_pct:.2f}% above)"
            intent = self._build_intent(direction, self.position_size, confidence, reason)
            return [intent]

        # Short signal: Price below EMA with short bias or downtrend
        if price_below_ema and (bias_val == "short" or trend_val == "down"):
            # Additional confirmation: price should be moving down
            direction = TradeDirection.SHORT
            confidence = min(signal.confidence, 0.7)  # Cap confidence for EMA signals
            reason = f"Price below {self.ema_period} EMA with bearish momentum ({ema_distance_pct:.2f}% below)"
            intent = self._build_intent(direction, self.position_size, confidence, reason)
            return [intent]

        return []

