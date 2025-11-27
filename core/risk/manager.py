from __future__ import annotations

from dataclasses import dataclass
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

    def reset_daily(self) -> None:
        """Reset daily tracking (call at start of each trading day)."""
        self.daily_pnl = 0.0

    def update_capital(self, pnl: float) -> None:
        """Update capital and track daily PnL."""
        self.current_capital += pnl
        self.daily_pnl += pnl
        self.recent_returns.append(pnl / self.current_capital if self.current_capital > 0 else 0.0)

        if pnl < 0:
            self.loss_streak += 1
        else:
            self.loss_streak = 0

    def check_daily_loss_limit(self) -> bool:
        """Return True if daily loss limit is exceeded."""
        loss_pct = abs(self.daily_pnl) / self.initial_capital if self.daily_pnl < 0 else 0.0
        return loss_pct >= self.config.max_daily_loss_pct

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

