"""Advanced risk management for challenge mode - avoids losing conditions."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Dict, Optional, Tuple

from core.regime.types import RegimeSignal, RegimeType, VolatilityLevel

logger = logging.getLogger(__name__)


@dataclass
class ChallengeRiskConfig:
    """Risk configuration for challenge mode."""
    
    # Daily limits
    max_daily_drawdown_pct: float = 10.0  # Stop trading if down 10% in a day
    max_daily_loss_pct: float = 15.0  # Hard stop at 15% daily loss
    min_daily_profit_pct: float = -5.0  # If down 5%, reduce aggression
    
    # Confidence gates
    min_confidence_for_trade: float = 0.75  # Only trade with high confidence
    min_confidence_for_leverage: float = 0.80  # Only use full leverage at 80%+ confidence
    
    # Volatility gates
    min_volatility_for_trade: str = "MEDIUM"  # Don't trade in low volatility
    max_volatility_for_trade: str = "EXTREME"  # Don't trade in extreme volatility (liquidation risk)
    
    # Regime filters
    allowed_regimes: list[RegimeType] = None  # Only trade in these regimes
    blocked_regimes: list[RegimeType] = None  # Never trade in these regimes
    
    # Session analysis
    avoid_choppy_hours: bool = True  # Avoid low-volume hours
    avoid_weekend_crypto: bool = True  # Avoid crypto weekends (low liquidity)
    avoid_market_open_close: bool = True  # Avoid first/last 30 min of trading day
    
    # Adaptive leverage
    base_leverage: float = 3.0
    max_leverage: float = 5.0
    min_leverage: float = 1.0
    leverage_volatility_scaling: bool = True  # Reduce leverage in high volatility
    
    # Kill switches
    enable_liquidation_cascade_detection: bool = True
    liquidation_cascade_threshold_pct: float = -5.0  # If down 5% in 5 minutes, kill switch
    
    def __post_init__(self):
        """Set defaults."""
        if self.allowed_regimes is None:
            # Default: Only trade trends and expansions
            self.allowed_regimes = [RegimeType.TREND, RegimeType.EXPANSION]
        
        if self.blocked_regimes is None:
            # Default: Block compression and mean reversion (too risky for challenge)
            self.blocked_regimes = [RegimeType.COMPRESSION]


class ChallengeRiskManager:
    """Manages risk and avoids losing conditions for challenge mode."""
    
    def __init__(self, config: Optional[ChallengeRiskConfig] = None):
        self.config = config or ChallengeRiskConfig()
        self.start_capital: float = 0.0
        self.current_capital: float = 0.0
        self.daily_start_capital: float = 0.0
        self.daily_pnl: float = 0.0
        self.last_trade_time: Optional[datetime] = None
        self.trades_today: int = 0
        self.last_reset_date: Optional[datetime] = None
        self.recent_returns: list[float] = []  # Track recent returns for cascade detection
        self.kill_switch_active: bool = False
        self.kill_switch_reason: str = ""
        
    def initialize(self, start_capital: float) -> None:
        """Initialize with starting capital."""
        self.start_capital = start_capital
        self.current_capital = start_capital
        self.daily_start_capital = start_capital
        self.daily_pnl = 0.0
        self.last_reset_date = datetime.now().date()
        self.kill_switch_active = False
        self.kill_switch_reason = ""
        logger.info(f"Challenge risk manager initialized with ${start_capital:.2f}")
    
    def update_capital(self, new_capital: float) -> None:
        """Update current capital and track daily PnL."""
        old_capital = self.current_capital
        self.current_capital = new_capital
        
        # Reset daily tracking if new day
        today = datetime.now().date()
        if self.last_reset_date != today:
            self.daily_start_capital = old_capital
            self.daily_pnl = 0.0
            self.trades_today = 0
            self.last_reset_date = today
            self.recent_returns.clear()
            logger.info(f"Daily reset: Starting capital = ${self.daily_start_capital:.2f}")
        
        # Update daily PnL
        self.daily_pnl = self.current_capital - self.daily_start_capital
        
        # Track recent returns for cascade detection
        if old_capital > 0:
            recent_return = ((new_capital - old_capital) / old_capital) * 100.0
            self.recent_returns.append((datetime.now(), recent_return))
            # Keep only last 10 minutes
            cutoff = datetime.now() - timedelta(minutes=10)
            self.recent_returns = [(t, r) for t, r in self.recent_returns if t > cutoff]
    
    def can_trade(
        self,
        signal: RegimeSignal,
        market_state: Dict,
        current_time: Optional[datetime] = None,
    ) -> Tuple[bool, str]:
        """
        Check if trading is allowed given current conditions.
        
        Returns:
            (can_trade, reason)
        """
        if current_time is None:
            current_time = datetime.now()
        
        # Check kill switch first
        if self.kill_switch_active:
            return False, f"Kill switch active: {self.kill_switch_reason}"
        
        # Check daily drawdown limit
        if self.daily_start_capital > 0:
            daily_drawdown_pct = (abs(self.daily_pnl) / self.daily_start_capital) * 100.0 if self.daily_pnl < 0 else 0.0
            
            if daily_drawdown_pct >= self.config.max_daily_drawdown_pct:
                self._activate_kill_switch(f"Daily drawdown limit: {daily_drawdown_pct:.2f}%")
                return False, f"Daily drawdown limit exceeded: {daily_drawdown_pct:.2f}%"
            
            if daily_drawdown_pct >= self.config.max_daily_loss_pct:
                self._activate_kill_switch(f"Daily loss limit: {daily_drawdown_pct:.2f}%")
                return False, f"Daily loss limit exceeded: {daily_drawdown_pct:.2f}%"
        
        # Check confidence gate
        if signal.confidence < self.config.min_confidence_for_trade:
            return False, f"Confidence too low: {signal.confidence:.2f} < {self.config.min_confidence_for_trade}"
        
        # Check regime filters
        if signal.regime_type in self.config.blocked_regimes:
            return False, f"Blocked regime: {signal.regime_type.value}"
        
        if self.config.allowed_regimes and signal.regime_type not in self.config.allowed_regimes:
            return False, f"Regime not allowed: {signal.regime_type.value}"
        
        # Check volatility gate
        vol_level = signal.volatility_level.value
        if vol_level == "LOW":
            return False, "Volatility too low for trading"
        
        if vol_level == "EXTREME" and self.config.max_volatility_for_trade == "EXTREME":
            return False, "Volatility too extreme (liquidation risk)"
        
        # Check session analysis
        session_check, session_reason = self._check_session_conditions(current_time, market_state)
        if not session_check:
            return False, session_reason
        
        # Check liquidation cascade
        if self.config.enable_liquidation_cascade_detection:
            cascade_check, cascade_reason = self._check_liquidation_cascade()
            if not cascade_check:
                return False, cascade_reason
        
        # Check if we're in a losing streak
        if len(self.recent_returns) >= 3:
            recent_losses = [r for _, r in self.recent_returns[-3:] if r < 0]
            if len(recent_losses) >= 3:
                return False, "Three consecutive losses - pausing"
        
        return True, "OK"
    
    def get_adaptive_leverage(
        self,
        signal: RegimeSignal,
        market_state: Dict,
    ) -> float:
        """
        Calculate adaptive leverage based on conditions.
        
        Returns:
            Leverage multiplier (1.0 to max_leverage)
        """
        leverage = self.config.base_leverage
        
        # Confidence scaling
        if signal.confidence < self.config.min_confidence_for_leverage:
            # Reduce leverage if confidence below threshold
            confidence_factor = signal.confidence / self.config.min_confidence_for_leverage
            leverage = leverage * confidence_factor
        
        # Volatility scaling
        if self.config.leverage_volatility_scaling:
            vol_level = signal.volatility_level.value
            if vol_level == "HIGH":
                leverage = leverage * 0.7  # Reduce leverage in high volatility
            elif vol_level == "EXTREME":
                leverage = leverage * 0.5  # Reduce more in extreme volatility
            elif vol_level == "MEDIUM":
                leverage = leverage * 0.9  # Slight reduction
        
        # Daily drawdown scaling
        if self.daily_start_capital > 0:
            daily_drawdown_pct = (abs(self.daily_pnl) / self.daily_start_capital) * 100.0 if self.daily_pnl < 0 else 0.0
            
            if daily_drawdown_pct > abs(self.config.min_daily_profit_pct):
                # If we're down, reduce leverage
                reduction = min(daily_drawdown_pct / 10.0, 0.5)  # Up to 50% reduction
                leverage = leverage * (1.0 - reduction)
        
        # Clamp to min/max
        leverage = max(self.config.min_leverage, min(leverage, self.config.max_leverage))
        
        return leverage
    
    def get_dynamic_profit_target(
        self,
        signal: RegimeSignal,
        market_state: Dict,
        base_profit_target: float,
    ) -> float:
        """
        Calculate dynamic profit target based on conditions.
        
        Args:
            signal: Current regime signal
            market_state: Market state dict
            base_profit_target: Base profit target (e.g., 12%)
        
        Returns:
            Adjusted profit target
        """
        target = base_profit_target
        
        # Increase target in high confidence, high volatility
        if signal.confidence >= 0.85 and signal.volatility_level.value in ["HIGH", "EXTREME"]:
            target = target * 1.2  # 20% increase
        
        # Decrease target if we're down for the day
        if self.daily_pnl < 0 and self.daily_start_capital > 0:
            daily_drawdown_pct = (abs(self.daily_pnl) / self.daily_start_capital) * 100.0
            if daily_drawdown_pct > 3.0:
                target = target * 0.8  # Take profits faster if down
        
        return target
    
    def _check_session_conditions(
        self,
        current_time: datetime,
        market_state: Dict,
    ) -> Tuple[bool, str]:
        """Check if current session conditions are favorable."""
        hour = current_time.hour
        minute = current_time.minute
        weekday = current_time.weekday()  # 0 = Monday, 6 = Sunday
        
        # Check if it's a weekend (for crypto)
        if weekday >= 5:  # Saturday or Sunday
            if self.config.avoid_weekend_crypto:
                # Check if we're trading crypto (would need symbol info, but assume crypto for now)
                return False, "Weekend trading avoided (low liquidity)"
        
        # Check market open/close (for equity)
        if self.config.avoid_market_open_close:
            # First 30 minutes (9:30 AM - 10:00 AM ET)
            if hour == 9 and minute < 30:
                return False, "Avoiding market open (first 30 min)"
            
            # Last 30 minutes (3:30 PM - 4:00 PM ET)
            if hour == 15 and minute >= 30:
                return False, "Avoiding market close (last 30 min)"
        
        # Check choppy hours (lunch time, low volume)
        if self.config.avoid_choppy_hours:
            # 12:00 PM - 1:30 PM ET (lunch time, lower volume)
            if hour == 12 or (hour == 13 and minute < 30):
                return False, "Avoiding choppy hours (lunch time)"
        
        return True, "OK"
    
    def _check_liquidation_cascade(self) -> Tuple[bool, str]:
        """Check for rapid losses indicating liquidation cascade."""
        if not self.config.enable_liquidation_cascade_detection:
            return True, "OK"
        
        if len(self.recent_returns) < 3:
            return True, "OK"
        
        # Check last 5 minutes
        cutoff = datetime.now() - timedelta(minutes=5)
        recent = [(t, r) for t, r in self.recent_returns if t > cutoff]
        
        if len(recent) >= 2:
            total_loss = sum(r for _, r in recent if r < 0)
            if total_loss <= self.config.liquidation_cascade_threshold_pct:
                self._activate_kill_switch(f"Liquidation cascade detected: {total_loss:.2f}% in 5 min")
                return False, f"Liquidation cascade: {total_loss:.2f}% loss in 5 minutes"
        
        return True, "OK"
    
    def _activate_kill_switch(self, reason: str) -> None:
        """Activate kill switch to stop all trading."""
        if not self.kill_switch_active:
            self.kill_switch_active = True
            self.kill_switch_reason = reason
            logger.error(f"🚨 KILL SWITCH ACTIVATED: {reason}")
    
    def reset_kill_switch(self) -> None:
        """Reset kill switch (manual intervention required)."""
        self.kill_switch_active = False
        self.kill_switch_reason = ""
        logger.info("Kill switch reset")
    
    def record_trade(self, is_win: bool) -> None:
        """Record a trade (for win rate tracking)."""
        # Note: Trade counting is handled by the agent
        # This is for win/loss tracking if needed
        pass
    
    def get_risk_status(self) -> Dict:
        """Get current risk status."""
        daily_drawdown_pct = 0.0
        if self.daily_start_capital > 0:
            daily_drawdown_pct = (abs(self.daily_pnl) / self.daily_start_capital) * 100.0 if self.daily_pnl < 0 else 0.0
        
        return {
            "kill_switch_active": self.kill_switch_active,
            "kill_switch_reason": self.kill_switch_reason,
            "daily_drawdown_pct": daily_drawdown_pct,
            "daily_pnl": self.daily_pnl,
            "trades_today": self.trades_today,
            "current_capital": self.current_capital,
            "daily_start_capital": self.daily_start_capital,
        }

