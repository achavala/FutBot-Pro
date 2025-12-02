"""Multi-leg options profit-taking and exit management."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from core.regime.types import RegimeSignal
from core.regime.microstructure import MarketMicrostructure

logger = logging.getLogger(__name__)


@dataclass
class MultiLegProfitConfig:
    """Configuration for multi-leg profit-taking logic."""
    
    # Theta Harvester (straddle seller) rules
    theta_take_profit_pct: float = 50.0  # Take profit at 50% of credit
    theta_stop_loss_pct: float = 200.0  # Stop loss at 200% of credit (2x credit)
    theta_iv_collapse_threshold: float = 0.3  # Exit if IV drops 30% from entry
    
    # Gamma Scalper (strangle buyer) rules
    gamma_take_profit_pct: float = 150.0  # Take profit at 150% gain
    gamma_stop_loss_pct: float = 50.0  # Stop loss at 50% loss
    gamma_gex_reversal_threshold: float = 1.0  # Exit if GEX flips from negative to positive (billions)
    
    # Common rules
    min_hold_bars: int = 5  # Minimum hold time
    max_hold_bars: int = 390  # Maximum hold time (~6.5 hours for 1-min bars)


@dataclass
class MultiLegPositionTracker:
    """Tracks a multi-leg position for profit-taking."""
    
    multi_leg_id: str
    strategy: str  # "theta_harvester" or "gamma_scalper"
    direction: str  # "long" or "short"
    entry_time: datetime
    entry_bar: int
    net_premium: float  # Credit for short, debit for long
    entry_iv: float  # IV at entry (for IV collapse detection)
    entry_gex_strength: float  # GEX strength at entry (for Gamma Scalper)
    peak_profit_pct: float = 0.0  # Best profit percentage achieved
    
    def update(self, current_profit_pct: float) -> None:
        """Update position with current profit percentage."""
        if current_profit_pct > self.peak_profit_pct:
            self.peak_profit_pct = current_profit_pct


class MultiLegProfitManager:
    """Manages profit-taking and exit logic for multi-leg options positions."""
    
    def __init__(
        self,
        config: Optional[MultiLegProfitConfig] = None,
        options_data_feed=None,
    ):
        """
        Initialize multi-leg profit manager.
        
        Args:
            config: Optional profit config
            options_data_feed: Options data feed for IV calculations
        """
        self.config = config or MultiLegProfitConfig()
        self.options_data_feed = options_data_feed
        self.positions: dict[str, MultiLegPositionTracker] = {}
        self.microstructure = MarketMicrostructure()
    
    def track_position(
        self,
        multi_leg_id: str,
        strategy: str,
        direction: str,
        net_premium: float,
        entry_time: datetime,
        entry_bar: int,
        entry_iv: Optional[float] = None,
        entry_gex_strength: Optional[float] = None,
    ) -> None:
        """Start tracking a new multi-leg position."""
        self.positions[multi_leg_id] = MultiLegPositionTracker(
            multi_leg_id=multi_leg_id,
            strategy=strategy,
            direction=direction,
            entry_time=entry_time,
            entry_bar=entry_bar,
            net_premium=net_premium,
            entry_iv=entry_iv or 0.0,
            entry_gex_strength=entry_gex_strength or 0.0,
        )
        logger.info(
            f"📊 [MultiLegProfit] Tracking {strategy} position: {multi_leg_id}, "
            f"premium=${net_premium:.2f}, IV={entry_iv:.1%} if entry_iv else 'N/A'}"
        )
    
    def should_take_profit(
        self,
        multi_leg_id: str,
        current_pnl_pct: float,
        current_bar: int,
        current_regime: Optional[RegimeSignal] = None,
        symbol: Optional[str] = None,
    ) -> tuple[bool, str]:
        """
        Check if multi-leg position should be closed for profit-taking.
        
        Returns:
            (should_close, reason)
        """
        if multi_leg_id not in self.positions:
            return False, ""
        
        tracker = self.positions[multi_leg_id]
        bars_held = current_bar - tracker.entry_bar
        
        # Check minimum hold time
        if bars_held < self.config.min_hold_bars:
            return False, ""
        
        # Check maximum hold time
        if bars_held >= self.config.max_hold_bars:
            return True, f"Maximum hold time reached ({bars_held} bars)"
        
        # Update peak profit
        tracker.update(current_pnl_pct)
        
        # Strategy-specific exit rules
        if tracker.strategy == "theta_harvester":
            return self._check_theta_harvester_exit(
                tracker, current_pnl_pct, current_regime, symbol
            )
        elif tracker.strategy == "gamma_scalper":
            return self._check_gamma_scalper_exit(
                tracker, current_pnl_pct, current_regime, symbol
            )
        
        return False, ""
    
    def _check_theta_harvester_exit(
        self,
        tracker: MultiLegPositionTracker,
        current_pnl_pct: float,
        current_regime: Optional[RegimeSignal],
        symbol: Optional[str],
    ) -> tuple[bool, str]:
        """
        Check exit conditions for Theta Harvester (straddle seller).
        
        Rules:
        - Take profit at 50% of credit
        - Stop loss at 200% of credit (2x credit)
        - Exit if IV collapses (drops 30% from entry)
        """
        # Take profit: 50% of credit
        if current_pnl_pct >= self.config.theta_take_profit_pct:
            return True, f"Theta Harvester TP: {current_pnl_pct:.1f}% profit (target: {self.config.theta_take_profit_pct}%)"
        
        # Stop loss: 200% of credit (2x credit loss)
        if current_pnl_pct <= -self.config.theta_stop_loss_pct:
            return True, f"Theta Harvester SL: {current_pnl_pct:.1f}% loss (limit: {self.config.theta_stop_loss_pct}%)"
        
        # IV collapse check
        if symbol and self.options_data_feed and tracker.entry_iv > 0:
            try:
                # Get current IV from options chain
                options_chain = self.options_data_feed.get_options_chain(
                    underlying_symbol=symbol,
                    option_type="call",
                )
                
                if options_chain:
                    # Find ATM call to get current IV
                    current_price = None
                    if current_regime and hasattr(current_regime, 'metrics'):
                        current_price = current_regime.metrics.get('close')
                    
                    if current_price:
                        for option in options_chain:
                            strike = float(option.get("strike_price", 0))
                            if abs(strike - current_price) / current_price < 0.02:  # ATM
                                option_symbol = option.get("symbol", "")
                                if option_symbol:
                                    greeks = self.options_data_feed.get_option_greeks(option_symbol)
                                    if greeks:
                                        current_iv = greeks.get("implied_volatility", 0.0)
                                        if current_iv > 0:
                                            iv_change_pct = ((current_iv - tracker.entry_iv) / tracker.entry_iv) * 100.0
                                            
                                            # IV collapsed (dropped 30%+)
                                            if iv_change_pct <= -self.config.theta_iv_collapse_threshold * 100:
                                                return True, (
                                                    f"Theta Harvester IV collapse: "
                                                    f"IV dropped {abs(iv_change_pct):.1f}% "
                                                    f"({tracker.entry_iv:.1%} → {current_iv:.1%})"
                                                )
            except Exception as e:
                logger.debug(f"Error checking IV collapse: {e}")
        
        # Regime change: exit if compression regime ends
        if current_regime:
            regime_type = current_regime.regime_type.value if hasattr(current_regime.regime_type, 'value') else str(current_regime.regime_type)
            if regime_type != "compression":
                return True, f"Theta Harvester regime exit: compression ended (now: {regime_type})"
        
        return False, ""
    
    def _check_gamma_scalper_exit(
        self,
        tracker: MultiLegPositionTracker,
        current_pnl_pct: float,
        current_regime: Optional[RegimeSignal],
        symbol: Optional[str],
    ) -> tuple[bool, str]:
        """
        Check exit conditions for Gamma Scalper (strangle buyer).
        
        Rules:
        - Take profit at 100-200% gain
        - Stop loss at 50% loss
        - Exit if GEX flips from negative to positive
        """
        # Take profit: 150% gain
        if current_pnl_pct >= self.config.gamma_take_profit_pct:
            return True, f"Gamma Scalper TP: {current_pnl_pct:.1f}% profit (target: {self.config.gamma_take_profit_pct}%)"
        
        # Stop loss: 50% loss
        if current_pnl_pct <= -self.config.gamma_stop_loss_pct:
            return True, f"Gamma Scalper SL: {current_pnl_pct:.1f}% loss (limit: {self.config.gamma_stop_loss_pct}%)"
        
        # GEX reversal check
        if symbol:
            try:
                gex = self.microstructure.get(symbol)
                current_gex_regime = gex.get('gex_regime', 'NEUTRAL')
                current_gex_strength = gex.get('gex_strength', 0.0)
                
                # Entry was negative GEX, now check if it flipped
                if tracker.entry_gex_strength < 0:  # Was negative
                    if current_gex_regime == "POSITIVE" and current_gex_strength >= self.config.gamma_gex_reversal_threshold:
                        return True, (
                            f"Gamma Scalper GEX reversal: "
                            f"GEX flipped from negative ({tracker.entry_gex_strength:.2f}B) "
                            f"to positive ({current_gex_strength:.2f}B)"
                        )
            except Exception as e:
                logger.debug(f"Error checking GEX reversal: {e}")
        
        return False, ""
    
    def remove_position(self, multi_leg_id: str) -> None:
        """Stop tracking a position (after it's closed)."""
        if multi_leg_id in self.positions:
            tracker = self.positions[multi_leg_id]
            logger.info(
                f"📊 [MultiLegProfit] Stopped tracking: {multi_leg_id}, "
                f"peak profit: {tracker.peak_profit_pct:.1f}%"
            )
            del self.positions[multi_leg_id]
    
    def get_position_info(self, multi_leg_id: str) -> Optional[dict]:
        """Get current position tracking info."""
        if multi_leg_id not in self.positions:
            return None
        
        tracker = self.positions[multi_leg_id]
        return {
            "multi_leg_id": tracker.multi_leg_id,
            "strategy": tracker.strategy,
            "direction": tracker.direction,
            "entry_time": tracker.entry_time.isoformat(),
            "net_premium": tracker.net_premium,
            "entry_iv": tracker.entry_iv,
            "entry_gex_strength": tracker.entry_gex_strength,
            "peak_profit_pct": tracker.peak_profit_pct,
            "entry_bar": tracker.entry_bar,
        }


