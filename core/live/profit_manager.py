"""Profit-taking and exit management for live trading."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from core.regime.types import RegimeSignal, RegimeType, Bias

if TYPE_CHECKING:
    from core.config.asset_profiles import AssetProfile

logger = logging.getLogger(__name__)


@dataclass
class ProfitConfig:
    """Configuration for profit-taking logic."""
    
    # Profit targets
    take_profit_pct: float = 15.0  # Take profit at 15% gain
    stop_loss_pct: float = 10.0  # Stop loss at 10% loss
    trailing_stop_pct: float = 1.5  # Trailing stop at 1.5% from peak
    
    # Exit conditions
    exit_on_regime_change: bool = True  # Exit if regime becomes unfavorable
    exit_on_bias_flip: bool = True  # Exit if bias flips opposite direction
    
    # Minimum hold time (bars)
    min_hold_bars: int = 5  # Hold for at least 5 bars
    
    # Maximum hold time (bars) - force exit
    max_hold_bars: int = 200  # Force exit after 200 bars (~3.3 hours for 1-min bars)


@dataclass
class PositionTracker:
    """Tracks a position for profit-taking."""
    
    symbol: str
    entry_price: float
    entry_time: datetime
    entry_bar: int
    quantity: float
    peak_price: float  # Highest price since entry
    peak_profit_pct: float = 0.0  # Best profit percentage achieved
    
    def update(self, current_price: float) -> None:
        """Update position with current price."""
        if self.quantity > 0:  # Long position
            profit_pct = ((current_price - self.entry_price) / self.entry_price) * 100.0
            if current_price > self.peak_price:
                self.peak_price = current_price
                self.peak_profit_pct = profit_pct
        else:  # Short position
            profit_pct = ((self.entry_price - current_price) / self.entry_price) * 100.0
            if current_price < self.peak_price:
                self.peak_price = current_price
                self.peak_profit_pct = profit_pct


class ProfitManager:
    """Manages profit-taking and exit logic."""
    
    def __init__(
        self,
        config: Optional[ProfitConfig] = None,
        asset_profiles: Optional[dict[str, "AssetProfile"]] = None,
    ):
        """
        Initialize profit manager.
        
        Args:
            config: Optional default profit config (used if no asset profile)
            asset_profiles: Optional dict mapping symbol -> AssetProfile
        """
        self.config = config or ProfitConfig()
        self.asset_profiles = asset_profiles or {}
        self.positions: dict[str, PositionTracker] = {}
    
    def track_position(
        self,
        symbol: str,
        entry_price: float,
        quantity: float,
        entry_time: datetime,
        entry_bar: int,
    ) -> None:
        """Start tracking a new position."""
        self.positions[symbol] = PositionTracker(
            symbol=symbol,
            entry_price=entry_price,
            entry_time=entry_time,
            entry_bar=entry_bar,
            quantity=quantity,
            peak_price=entry_price,
        )
        logger.info(f"Tracking position: {symbol} @ ${entry_price:.2f}, qty={quantity:.2f}")
    
    def update_position(self, symbol: str, current_price: float, current_bar: int) -> None:
        """Update position with current price."""
        if symbol in self.positions:
            self.positions[symbol].update(current_price)
    
    def should_take_profit(
        self,
        symbol: str,
        current_price: float,
        current_bar: int,
        current_regime: Optional[RegimeSignal] = None,
    ) -> tuple[bool, str]:
        """
        Check if position should be closed for profit-taking.
        
        Returns:
            (should_close, reason)
        """
        if symbol not in self.positions:
            return False, ""
        
        tracker = self.positions[symbol]
        bars_held = current_bar - tracker.entry_bar
        
        # Check minimum hold time
        if bars_held < self.config.min_hold_bars:
            return False, ""
        
        # Check maximum hold time
        if bars_held >= self.config.max_hold_bars:
            return True, f"Maximum hold time reached ({bars_held} bars)"
        
        # Calculate current profit/loss
        # CRITICAL FIX: Prevent division by zero if entry_price is 0 or invalid
        if tracker.entry_price <= 0:
            logger.warning(f"⚠️ [ProfitManager] Invalid entry_price {tracker.entry_price} for {symbol}, skipping profit calculation")
            return False, ""
        
        if tracker.quantity > 0:  # Long
            profit_pct = ((current_price - tracker.entry_price) / tracker.entry_price) * 100.0
        else:  # Short
            profit_pct = ((tracker.entry_price - current_price) / tracker.entry_price) * 100.0
        
        # Check stop loss first (protect against large losses)
        if profit_pct <= -self.config.stop_loss_pct:
            return True, f"Stop loss triggered ({profit_pct:.2f}% loss)"
        
        # Check take profit target
        if profit_pct >= self.config.take_profit_pct:
            return True, f"Take profit target reached ({profit_pct:.2f}%)"
        
        # Check trailing stop
        if tracker.peak_profit_pct > self.config.take_profit_pct:
            # We've hit profit target, now check trailing stop
            drawdown_from_peak = tracker.peak_profit_pct - profit_pct
            if drawdown_from_peak >= self.config.trailing_stop_pct:
                return True, f"Trailing stop triggered ({drawdown_from_peak:.2f}% from peak)"
        
        # Check regime change exit
        if self.config.exit_on_regime_change and current_regime:
            # Exit if regime becomes unfavorable
            if tracker.quantity > 0:  # Long position
                # Exit if bias becomes bearish or regime becomes unfavorable
                if current_regime.bias == Bias.SHORT:
                    return True, "Regime bias flipped to bearish"
                if current_regime.regime_type == RegimeType.COMPRESSION and current_regime.confidence < 0.5:
                    return True, "Regime became uncertain (compression)"
            else:  # Short position
                # Exit if bias becomes bullish
                if current_regime.bias == Bias.LONG:
                    return True, "Regime bias flipped to bullish"
                if current_regime.regime_type == RegimeType.COMPRESSION and current_regime.confidence < 0.5:
                    return True, "Regime became uncertain (compression)"
        
        return False, ""
    
    def remove_position(self, symbol: str) -> None:
        """Stop tracking a position (after it's closed)."""
        if symbol in self.positions:
            tracker = self.positions[symbol]
            logger.info(
                f"Stopped tracking position: {symbol}, "
                f"peak profit: {tracker.peak_profit_pct:.2f}%"
            )
            del self.positions[symbol]
    
    def get_position_info(self, symbol: str) -> Optional[dict]:
        """Get current position tracking info."""
        if symbol not in self.positions:
            return None
        
        tracker = self.positions[symbol]
        return {
            "symbol": tracker.symbol,
            "entry_price": tracker.entry_price,
            "entry_time": tracker.entry_time.isoformat(),
            "quantity": tracker.quantity,
            "peak_price": tracker.peak_price,
            "peak_profit_pct": tracker.peak_profit_pct,
            "entry_bar": tracker.entry_bar,
        }
