"""Challenge mode configuration and management for 20-day $1K to $100K challenge."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ChallengeConfig:
    """Configuration for 20-day challenge mode."""
    
    initial_capital: float = 1000.0  # Starting capital
    target_capital: float = 100000.0  # Target capital
    trading_days: int = 20  # Number of trading days
    
    # Daily return target (compounded)
    daily_return_target_pct: float = 26.0  # ~26% per day to reach 10,000% in 20 days
    
    # Aggressive risk parameters
    profit_target_pct: float = 12.0  # Take profit at 12%
    stop_loss_pct: float = 6.0  # Stop loss at 6%
    leverage_multiplier: float = 3.0  # 3x leverage (options/margin)
    
    # Trading limits
    max_trades_per_day: int = 5  # Maximum trades per day
    max_position_size_pct: float = 50.0  # Max 50% of capital per position (with leverage)
    min_confidence: float = 0.6  # Minimum confidence for entry
    
    # Asset preferences (for challenge mode)
    preferred_asset_types: list[str] = None  # ["crypto", "options", "equity"]
    
    def __post_init__(self):
        """Calculate derived values."""
        if self.preferred_asset_types is None:
            # Default: prefer crypto and options for high volatility
            self.preferred_asset_types = ["crypto", "equity"]
        
        # Calculate required daily return
        if self.trading_days > 0:
            required_multiplier = self.target_capital / self.initial_capital
            daily_multiplier = required_multiplier ** (1.0 / self.trading_days)
            self.daily_return_target_pct = (daily_multiplier - 1.0) * 100.0


class ChallengeTracker:
    """Tracks progress toward challenge goal."""
    
    def __init__(self, config: ChallengeConfig):
        self.config = config
        self.start_date: Optional[datetime] = None
        self.start_capital: float = config.initial_capital
        self.current_capital: float = config.initial_capital
        self.current_day: int = 0
        self.total_trades: int = 0
        self.winning_trades: int = 0
        self.losing_trades: int = 0
        self.total_return_pct: float = 0.0
        self.daily_returns: list[float] = []
        
    def start(self) -> None:
        """Start the challenge."""
        self.start_date = datetime.now()
        self.current_capital = self.start_capital
        self.current_day = 0
        logger.info(f"Challenge started: ${self.start_capital:.2f} → ${self.config.target_capital:.2f} in {self.config.trading_days} days")
    
    def update_capital(self, new_capital: float) -> None:
        """Update current capital."""
        old_capital = self.current_capital
        self.current_capital = new_capital
        self.total_return_pct = ((self.current_capital - self.start_capital) / self.start_capital) * 100.0
        
        if self.start_date:
            days_elapsed = (datetime.now() - self.start_date).days
            if days_elapsed > 0:
                daily_return = ((self.current_capital / old_capital) - 1.0) * 100.0 if old_capital > 0 else 0.0
                self.daily_returns.append(daily_return)
    
    def sync_with_risk_manager(self, risk_manager: "ChallengeRiskManager") -> None:
        """Sync tracker with risk manager capital."""
        if risk_manager:
            self.current_capital = risk_manager.current_capital
            self.total_return_pct = ((self.current_capital - self.start_capital) / self.start_capital) * 100.0
    
    def record_trade(self, is_win: bool) -> None:
        """Record a trade result."""
        self.total_trades += 1
        if is_win:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
    
    def get_progress(self) -> dict:
        """Get current progress."""
        if not self.start_date:
            return {
                "status": "not_started",
                "current_capital": self.current_capital,
                "target_capital": self.config.target_capital,
                "progress_pct": 0.0,
            }
        
        days_elapsed = (datetime.now() - self.start_date).days
        days_remaining = max(0, self.config.trading_days - days_elapsed)
        
        # Calculate progress
        progress_pct = (self.current_capital / self.config.target_capital) * 100.0
        
        # Calculate required daily return from here
        if days_remaining > 0 and self.current_capital > 0:
            required_multiplier = self.config.target_capital / self.current_capital
            required_daily_return = (required_multiplier ** (1.0 / days_remaining) - 1.0) * 100.0
        else:
            required_daily_return = 0.0
        
        # Calculate average daily return so far
        avg_daily_return = sum(self.daily_returns) / len(self.daily_returns) if self.daily_returns else 0.0
        
        return {
            "status": "active" if days_remaining > 0 else "completed",
            "start_date": self.start_date.isoformat(),
            "days_elapsed": days_elapsed,
            "days_remaining": days_remaining,
            "start_capital": self.start_capital,
            "current_capital": self.current_capital,
            "target_capital": self.config.target_capital,
            "progress_pct": progress_pct,
            "total_return_pct": self.total_return_pct,
            "required_daily_return_pct": required_daily_return,
            "avg_daily_return_pct": avg_daily_return,
            "total_trades": self.total_trades,
            "win_rate": (self.winning_trades / self.total_trades * 100.0) if self.total_trades > 0 else 0.0,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
        }
    
    def is_on_track(self) -> bool:
        """Check if challenge is on track."""
        progress = self.get_progress()
        if progress["status"] != "active":
            return False
        
        # Check if we're meeting daily return target
        avg_daily_return = progress["avg_daily_return_pct"]
        required_daily_return = progress["required_daily_return_pct"]
        
        # On track if average daily return >= required daily return
        return avg_daily_return >= required_daily_return or avg_daily_return >= self.config.daily_return_target_pct

