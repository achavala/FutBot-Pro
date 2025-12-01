from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Deque, Optional

from collections import deque


@dataclass
class RiskConfig:
    """Configuration for risk management rules."""

    max_daily_loss_pct: float = 0.02  # 2% max daily loss
    max_loss_streak: int = 5
    max_position_size_pct: float = 0.1  # 10% of capital per position
    min_confidence_threshold: float = 0.4
    kill_switch: bool = False
    cvar_window: int = 20  # window for CVaR calculation
    cvar_percentile: float = 0.05  # 5th percentile for CVaR


class RiskManager:
    """Manages risk constraints and position sizing."""

    def __init__(self, initial_capital: float, config: Optional[RiskConfig] = None):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.config = config or RiskConfig()
        self.daily_pnl: float = 0.0
        self.loss_streak: int = 0
        self.recent_returns: Deque[float] = deque(maxlen=self.config.cvar_window)
        self.kill_switch_engaged = self.config.kill_switch
        
        # Daily loss cap tracking (for GEX v2 guard)
        self.base_daily_loss_cap = self.config.max_daily_loss_pct
        self.current_daily_loss_cap = self.config.max_daily_loss_pct
        
        # GEX v2: Extreme negative GEX guard tracking
        self._gex_guard_date: Optional[date] = None
        self._gex_reduced_today: bool = False
        
        # Logger for GEX guard warnings
        import logging
        self.logger = logging.getLogger(__name__)

    def reset_daily(self) -> None:
        """Reset daily tracking (call at start of each trading day)."""
        self.daily_pnl = 0.0
        # Reset daily loss cap to base value
        self.current_daily_loss_cap = self.base_daily_loss_cap
        # Reset GEX guard for new trading day
        self._gex_guard_date = None
        self._gex_reduced_today = False

    def update_capital(self, pnl: float) -> None:
        """Update capital and track daily PnL."""
        self.current_capital += pnl
        self.daily_pnl += pnl
        self.recent_returns.append(pnl / self.current_capital if self.current_capital > 0 else 0.0)

        if pnl < 0:
            self.loss_streak += 1
        else:
            self.loss_streak = 0

    def check_daily_loss_limit(self, symbol: Optional[str] = None) -> bool:
        """
        Return True if daily loss limit is exceeded.
        
        Includes GEX v2: Extreme Negative GEX Guard
        If extreme negative GEX (>$5B) and we're losing money, reduce daily loss limit.
        """
        # ==========================
        # Extreme Negative GEX Guard
        # ==========================
        today = date.today()

        if not self._gex_guard_date or self._gex_guard_date != today:
            self._gex_guard_date = today
            self._gex_reduced_today = False
            # Reset daily loss cap at start of new day
            self.current_daily_loss_cap = self.base_daily_loss_cap

        # Check for extreme negative GEX condition (if symbol provided)
        if symbol and not self._gex_reduced_today and self.daily_pnl < 0:
            try:
                from core.regime.microstructure import MarketMicrostructure
                microstructure = MarketMicrostructure()
                gex = microstructure.get(symbol)

                if (gex['gex_regime'] == 'NEGATIVE' and
                    gex['gex_strength'] > 5.0):
                    # Halve the daily loss cap for today
                    self.current_daily_loss_cap = self.current_daily_loss_cap * 0.5
                    self._gex_reduced_today = True
                    self.logger.warning(
                        f"[RISK] Extreme NEGATIVE GEX ({gex['gex_strength']:.2f}B) → daily loss cap HALVED "
                        f"from {self.base_daily_loss_cap:.2%} to {self.current_daily_loss_cap:.2%}"
                    )
            except Exception as e:
                # If microstructure not available, continue normally
                self.logger.debug(f"Could not check GEX guard: {e}")
        
        loss_pct = abs(self.daily_pnl) / self.initial_capital if self.daily_pnl < 0 else 0.0
        return loss_pct >= self.current_daily_loss_cap

    def check_loss_streak(self) -> bool:
        """Return True if loss streak limit is exceeded."""
        return self.loss_streak >= self.config.max_loss_streak

    def compute_cvar_position_size(self, base_size: float) -> float:
        """Adjust position size based on CVaR of recent returns."""
        if len(self.recent_returns) < 5:
            return base_size

        returns_list = sorted(self.recent_returns)
        cutoff_idx = int(len(returns_list) * self.config.cvar_percentile)
        if cutoff_idx == 0:
            cutoff_idx = 1
        tail_returns = returns_list[:cutoff_idx]
        cvar = sum(tail_returns) / len(tail_returns) if tail_returns else 0.0

        # Reduce size if CVaR is very negative
        if cvar < -0.01:  # 1% average tail loss
            reduction = min(abs(cvar) * 10, 0.5)  # reduce by up to 50%
            return base_size * (1 - reduction)

        return base_size

    def compute_position_size(self, position_delta: float, price: float, confidence: float) -> float:
        """Compute actual position size considering risk constraints."""
        if self.kill_switch_engaged:
            return 0.0

        if confidence < self.config.min_confidence_threshold:
            return 0.0

        if self.check_daily_loss_limit() or self.check_loss_streak():
            return 0.0

        # Base size as percentage of capital
        base_size_pct = abs(position_delta) * self.config.max_position_size_pct
        base_size = (self.current_capital * base_size_pct) / price if price > 0 else 0.0

        # Apply CVaR adjustment
        adjusted_size = self.compute_cvar_position_size(base_size)

        # Apply confidence scaling
        confidence_scaled = adjusted_size * confidence

        return confidence_scaled * (1.0 if position_delta >= 0 else -1.0)

    def can_trade(self, confidence: float) -> bool:
        """Check if trading is allowed given current risk state."""
        if self.kill_switch_engaged:
            return False
        if confidence < self.config.min_confidence_threshold:
            return False
        if self.check_daily_loss_limit():
            return False
        if self.check_loss_streak():
            return False
        return True

    def engage_kill_switch(self) -> None:
        """Engage emergency kill switch."""
        self.kill_switch_engaged = True

    def disengage_kill_switch(self) -> None:
        """Disengage kill switch."""
        self.kill_switch_engaged = False
    
    def calculate_theta_size(self, symbol: str, credit: float, underlying: float) -> int:
        """
        Calculate position size for theta harvesting (selling premium).
        
        Hybrid mode: Safe sizing for selling premium.
        Uses 0.2% of capital per straddle, capped conservatively.
        
        Args:
            symbol: Trading symbol
            credit: Total credit received for straddle (call bid + put bid)
            underlying: Current underlying price
            
        Returns:
            Position size in contracts (max 5 for hybrid mode)
        """
        if credit <= 0 or underlying <= 0:
            return 1
        
        # Risk unit: credit * contract multiplier (100)
        risk_unit = max(0.5, min(5, credit * 10))
        
        # Size based on 0.2% of capital per straddle
        size = int(self.current_capital * 0.002 / (risk_unit * 100))
        
        # Hybrid mode cap: max 5 contracts for safe sizing
        return max(1, min(size, 5))
    
    def calculate_gamma_scalp_size(self, debit: float, underlying: float) -> int:
        """
        Calculate position size for gamma scalping (buying premium).
        
        Hybrid mode: Aggressive but capped sizing.
        Uses 0.5% of capital per strangle, capped at 7 contracts.
        
        Args:
            debit: Total debit paid for strangle (call ask + put ask)
            underlying: Current underlying price
            
        Returns:
            Position size in contracts (max 7 for hybrid mode)
        """
        if debit <= 0 or underlying <= 0:
            return 1
        
        # Risk unit: debit * contract multiplier (100)
        risk_unit = max(1, debit * 10)
        
        # Size based on 0.5% of capital per strangle
        size = int(self.current_capital * 0.005 / (risk_unit * 100))
        
        # Hybrid mode cap: max 7 contracts (aggressive but safe)
        return max(1, min(size, 7))

