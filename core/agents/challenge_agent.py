"""Aggressive challenge mode agent for 20-day $1K to $100K challenge.
Enhanced with defensive filters to avoid losing conditions."""

from __future__ import annotations

import logging
from typing import Dict, List, Mapping, Optional

from core.agents.base import BaseAgent, TradeDirection, TradeIntent
from core.regime.types import RegimeSignal, RegimeType, Bias, TrendDirection

logger = logging.getLogger(__name__)


class ChallengeAgent(BaseAgent):
    """
    Aggressive agent for 20-day challenge mode.
    
    Strategy:
    - Targets 26% daily returns (compounded to 10,000% in 20 days)
    - Uses high leverage (options, margin, or crypto)
    - Fast turnaround trades (multiple per day)
    - High conviction entries only
    - Aggressive profit-taking (10-15% targets)
    - Tight stop losses (5-7%)
    """
    
    def __init__(
        self,
        symbol: str = "QQQ",
        config: Optional[Dict] = None,
        risk_manager: Optional["ChallengeRiskManager"] = None,
    ):
        """
        Initialize challenge agent with defensive filters.
        
        Args:
            symbol: Symbol to trade
            config: Configuration dict with:
                - min_confidence: Minimum confidence for entry (default: 0.75)
                - profit_target_pct: Profit target % (default: 12.0)
                - stop_loss_pct: Stop loss % (default: 6.0)
                - leverage_multiplier: Base leverage multiplier (default: 3.0)
                - max_trades_per_day: Maximum trades per day (default: 5)
            risk_manager: Optional ChallengeRiskManager for advanced filtering
        """
        super().__init__(name="ChallengeAgent", symbol=symbol)
        self.config = config or {}
        self.risk_manager = risk_manager
        
        # Higher confidence threshold for challenge mode
        self.min_confidence = self.config.get("min_confidence", 0.75)  # Increased from 0.6
        self.profit_target_pct = self.config.get("profit_target_pct", 12.0)  # 12% profit target
        self.stop_loss_pct = self.config.get("stop_loss_pct", 6.0)  # 6% stop loss
        self.base_leverage = self.config.get("leverage_multiplier", 3.0)  # Base leverage
        self.max_trades_per_day = self.config.get("max_trades_per_day", 5)
        
        self.trades_today = 0
        self.last_trade_date = None
        
        logger.info(
            f"ChallengeAgent initialized for {symbol}: "
            f"target={self.profit_target_pct}%, stop={self.stop_loss_pct}%, "
            f"base_leverage={self.base_leverage}x, min_confidence={self.min_confidence}"
        )
    
    def evaluate(
        self,
        signal: RegimeSignal,
        market_state: Mapping[str, float],
    ) -> List[TradeIntent]:
        """
        Evaluate aggressive trading opportunity with defensive filters.
        
        Entry conditions (ALL must be true):
        1. Risk manager allows trading (kill switch, drawdown limits, etc.)
        2. High confidence regime (>= min_confidence)
        3. Strong trend or momentum
        4. Clear bias direction
        5. Not at max trades per day
        6. Session conditions favorable
        7. No liquidation cascade detected
        
        Returns list of TradeIntent objects (typically 0 or 1).
        """
        from datetime import datetime
        
        # Reset daily trade count if new day
        today = datetime.now().date()
        if self.last_trade_date != today:
            self.trades_today = 0
            self.last_trade_date = today
        
        # Check max trades per day
        if self.trades_today >= self.max_trades_per_day:
            return []
        
        # DEFENSIVE FILTER #1: Risk manager check (kill switch, drawdown, etc.)
        if self.risk_manager:
            can_trade, reason = self.risk_manager.can_trade(signal, market_state)
            if not can_trade:
                logger.debug(f"ChallengeAgent: Risk manager blocked trade: {reason}")
                return []
        
        # DEFENSIVE FILTER #2: Require high confidence
        if signal.confidence < self.min_confidence:
            return []
        
        # DEFENSIVE FILTER #3: Require valid regime
        if not signal.is_valid:
            return []
        
        # DEFENSIVE FILTER #4: Only trade in favorable regimes
        # (Risk manager handles this, but double-check here)
        if signal.regime_type == RegimeType.COMPRESSION:
            return []  # Never trade compression in challenge mode
        
        # Entry logic: Look for strong trends or high momentum
        price = market_state.get("close", market_state.get("price", 0.0))
        if price <= 0:
            return []
        
        # Calculate position size and direction based on regime and bias
        direction = None
        position_size = 0.0
        confidence = 0.0
        reason = ""
        
        # Strategy 1: Strong uptrend with long bias
        if (
            signal.regime_type == RegimeType.TREND
            and signal.trend_direction == TrendDirection.UP
            and signal.bias == Bias.LONG
            and signal.confidence >= 0.7
        ):
            # Strong bullish trend - go long aggressively
            direction = TradeDirection.LONG
            position_size = 1.0 * self.base_leverage  # Leveraged position size
            confidence = signal.confidence * 0.9  # Slightly reduce for leverage risk
            reason = f"Strong uptrend (confidence: {signal.confidence:.2f})"
        
        # Strategy 2: Strong downtrend with short bias
        elif (
            signal.regime_type == RegimeType.TREND
            and signal.trend_direction == TrendDirection.DOWN
            and signal.bias == Bias.SHORT
            and signal.confidence >= 0.7
        ):
            # Strong bearish trend - go short aggressively
            direction = TradeDirection.SHORT
            position_size = 1.0 * self.base_leverage
            confidence = signal.confidence * 0.9
            reason = f"Strong downtrend (confidence: {signal.confidence:.2f})"
        
        # Strategy 3: High volatility expansion with clear direction
        elif (
            signal.regime_type == RegimeType.EXPANSION
            and signal.confidence >= 0.75
            and (signal.volatility_level.value if hasattr(signal.volatility_level, 'value') else str(signal.volatility_level)) == "high"
        ):
            # High volatility expansion - trade with the bias
            if signal.bias == Bias.LONG:
                direction = TradeDirection.LONG
                position_size = 0.8 * self.base_leverage  # Slightly less aggressive
                confidence = signal.confidence * 0.85
                reason = f"Volatility expansion long (confidence: {signal.confidence:.2f})"
            elif signal.bias == Bias.SHORT:
                direction = TradeDirection.SHORT
                position_size = 0.8 * self.base_leverage
                confidence = signal.confidence * 0.85
                reason = f"Volatility expansion short (confidence: {signal.confidence:.2f})"
        
        # Strategy 4: Mean reversion with high confidence (more conservative)
        # Note: Mean reversion is blocked by risk manager, but keep for completeness
        elif (
            signal.regime_type == RegimeType.MEAN_REVERSION
            and signal.confidence >= 0.8
        ):
            # Mean reversion - trade against extreme moves
            # This is riskier, so use lower leverage
            if signal.bias == Bias.LONG:
                direction = TradeDirection.LONG
                position_size = 0.6 * self.base_leverage
                confidence = signal.confidence * 0.8
                reason = f"Mean reversion long (confidence: {signal.confidence:.2f})"
            elif signal.bias == Bias.SHORT:
                direction = TradeDirection.SHORT
                position_size = 0.6 * self.base_leverage
                confidence = signal.confidence * 0.8
                reason = f"Mean reversion short (confidence: {signal.confidence:.2f})"
        
        # If we have a valid trade, get adaptive leverage and dynamic profit target
        if direction is not None and position_size > 0:
            # DEFENSIVE FILTER #5: Adaptive leverage based on conditions
            if self.risk_manager:
                adaptive_leverage = self.risk_manager.get_adaptive_leverage(signal, market_state)
                # Adjust position size based on adaptive leverage
                position_size = (position_size / self.base_leverage) * adaptive_leverage
                
                # DEFENSIVE FILTER #6: Dynamic profit target
                dynamic_profit_target = self.risk_manager.get_dynamic_profit_target(
                    signal, market_state, self.profit_target_pct
                )
            else:
                adaptive_leverage = self.base_leverage
                dynamic_profit_target = self.profit_target_pct
            
            self.trades_today += 1
            metadata = {
                "profit_target_pct": dynamic_profit_target,
                "stop_loss_pct": self.stop_loss_pct,
                "leverage_multiplier": adaptive_leverage,
                "base_leverage": self.base_leverage,
            }
            logger.info(
                f"ChallengeAgent: Entry signal - {direction.value if hasattr(direction, 'value') else str(direction)}, "
                f"leverage={adaptive_leverage:.2f}x, "
                f"profit_target={dynamic_profit_target:.2f}%, "
                f"confidence={confidence:.2f}"
            )
            return [self._build_intent(direction, position_size, confidence, reason, metadata)]
        
        return []
    
    def get_profit_target_pct(self) -> float:
        """Get profit target percentage."""
        return self.profit_target_pct
    
    def get_stop_loss_pct(self) -> float:
        """Get stop loss percentage."""
        return self.stop_loss_pct
    
    def get_leverage_multiplier(self) -> float:
        """Get leverage multiplier."""
        return self.leverage_multiplier

