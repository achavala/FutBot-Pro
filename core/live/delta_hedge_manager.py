"""Delta hedging manager for Gamma Scalper positions."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.portfolio.options_manager import MultiLegPosition
    from core.live.broker_client import BaseBrokerClient

logger = logging.getLogger(__name__)


@dataclass
class DeltaHedgeConfig:
    """Configuration for delta hedging."""
    
    # Delta threshold for hedging (absolute value)
    delta_threshold: float = 0.10  # Hedge when |net_delta| > 0.10 per contract
    
    # Minimum delta change to trigger re-hedge (avoid over-trading)
    min_delta_change: float = 0.05  # Re-hedge only if delta changed by 0.05
    
    # Hedging frequency limit (bars between hedges)
    hedge_frequency_bars: int = 5  # Don't hedge more than once per 5 bars
    
    # Enable/disable hedging
    enabled: bool = True
    
    # Track hedging P&L separately
    track_hedge_pnl: bool = True
    
    # Guardrails
    max_hedge_trades_per_day: int = 50  # Max hedge trades per symbol per day
    max_hedge_notional_per_day: float = 100000.0  # Max hedge notional per symbol per day ($)
    min_hedge_shares: float = 5.0  # Minimum hedge size (avoid micro-hedges)
    
    # Hedge-only risk protection
    max_orphan_hedge_bars: int = 60  # Max bars to allow hedge without options (force flatten)


@dataclass
class HedgePosition:
    """Tracks a hedge position for a multi-leg options position."""
    
    multi_leg_id: str
    symbol: str
    
    # Current hedge state
    hedge_shares: float = 0.0  # Positive = long shares, negative = short shares
    hedge_avg_price: float = 0.0  # Average price of hedge position (for P&L calculation)
    last_hedge_price: float = 0.0  # Price of last hedge trade
    last_hedge_time: datetime = field(default_factory=datetime.now)
    last_hedge_bar: int = 0
    
    # Hedging P&L tracking
    hedge_realized_pnl: float = 0.0  # Realized P&L from closed hedge positions
    hedge_unrealized_pnl: float = 0.0  # Current unrealized P&L
    total_hedge_cost: float = 0.0  # Total cost of hedging (commissions, slippage)
    
    # Delta tracking
    last_net_delta: float = 0.0
    target_delta: float = 0.0  # Target is always 0 (delta-neutral)
    
    # Statistics
    hedge_count: int = 0  # Number of times hedged
    total_shares_traded: float = 0.0  # Total shares bought/sold (absolute)


class DeltaHedgeManager:
    """
    Manages delta hedging for Gamma Scalper multi-leg positions.
    
    Goal: Keep net delta near zero to extract pure volatility (gamma scalping)
    without directional bias.
    
    How it works:
    1. Calculate net delta of Gamma Scalper strangle positions
    2. When |net_delta| > threshold, hedge by buying/selling underlying
    3. Track hedging P&L separately from options P&L
    4. Re-hedge as delta changes with underlying movement
    """
    
    def __init__(
        self,
        config: Optional[DeltaHedgeConfig] = None,
        broker_client: Optional["BaseBrokerClient"] = None,
        timeline_logger: Optional["DeltaHedgeTimelineLogger"] = None,
    ):
        self.config = config or DeltaHedgeConfig()
        self.broker_client = broker_client
        self.timeline_logger = timeline_logger
        self.hedge_positions: Dict[str, HedgePosition] = {}  # key: multi_leg_id
        
        # Daily tracking for guardrails
        self.daily_hedge_trades: Dict[str, int] = {}  # key: symbol, value: count
        self.daily_hedge_notional: Dict[str, float] = {}  # key: symbol, value: notional
        self.current_day: Optional[str] = None  # YYYY-MM-DD format
        
        # Orphan hedge tracking (hedge without options)
        self.orphan_hedge_bars: Dict[str, int] = {}  # key: multi_leg_id, value: bars since options closed
    
    def calculate_net_delta(self, ml_pos: "MultiLegPosition") -> float:
        """
        Calculate net delta of a multi-leg position.
        
        For Gamma Scalper (long strangle):
        - Call delta is positive (e.g., +0.25)
        - Put delta is negative (e.g., -0.25)
        - Net delta = (call_delta * call_quantity) + (put_delta * put_quantity)
        
        Returns:
            Net delta (positive = long bias, negative = short bias)
        """
        if ml_pos.direction != "long":
            # Only hedge long strangles (Gamma Scalper)
            return 0.0
        
        # Calculate net delta
        # For long calls: positive delta
        # For long puts: negative delta
        call_delta_contribution = ml_pos.call_delta * ml_pos.call_quantity
        put_delta_contribution = ml_pos.put_delta * ml_pos.put_quantity
        
        net_delta = call_delta_contribution + put_delta_contribution
        
        logger.debug(
            f"[DeltaHedge] {ml_pos.multi_leg_id}: "
            f"call_delta={ml_pos.call_delta:.3f}*{ml_pos.call_quantity}={call_delta_contribution:.3f}, "
            f"put_delta={ml_pos.put_delta:.3f}*{ml_pos.put_quantity}={put_delta_contribution:.3f}, "
            f"net_delta={net_delta:.3f}"
        )
        
        return net_delta
    
    def should_hedge(
        self,
        multi_leg_id: str,
        net_delta: float,
        current_bar: int,
        current_price: float,
    ) -> tuple[bool, str]:
        """
        Determine if a position should be hedged.
        
        Returns:
            (should_hedge, reason)
        """
        if not self.config.enabled:
            return False, "Hedging disabled"
        
        if multi_leg_id not in self.hedge_positions:
            # First time checking this position
            if abs(net_delta) > self.config.delta_threshold:
                return True, f"Initial hedge: |delta|={abs(net_delta):.3f} > {self.config.delta_threshold}"
            return False, "Delta within threshold"
        
        hedge_pos = self.hedge_positions[multi_leg_id]
        
        # Check frequency limit
        bars_since_last_hedge = current_bar - hedge_pos.last_hedge_bar
        if bars_since_last_hedge < self.config.hedge_frequency_bars:
            return False, f"Frequency limit: {bars_since_last_hedge} < {self.config.hedge_frequency_bars} bars"
        
        # Check if delta exceeds threshold
        if abs(net_delta) <= self.config.delta_threshold:
            return False, f"Delta within threshold: |{net_delta:.3f}| <= {self.config.delta_threshold}"
        
        # Check if delta changed enough to warrant re-hedge
        delta_change = abs(net_delta - hedge_pos.last_net_delta)
        if delta_change < self.config.min_delta_change:
            return False, f"Delta change too small: {delta_change:.3f} < {self.config.min_delta_change}"
        
        return True, f"Re-hedge: |delta|={abs(net_delta):.3f} > {self.config.delta_threshold}, change={delta_change:.3f}"
    
    def calculate_hedge_quantity(self, net_delta: float, current_hedge_shares: float) -> float:
        """
        Calculate how many shares to buy/sell to hedge delta.
        
        Args:
            net_delta: Current net delta of options position (per contract, not multiplied)
            current_hedge_shares: Current hedge position (positive = long, negative = short)
        
        Returns:
            Shares to trade (positive = buy, negative = sell)
            To neutralize delta: target_hedge_shares = -net_delta * 100 (contract multiplier)
            Then: hedge_delta = target_hedge_shares - current_hedge_shares
        """
        # Target is delta-neutral (net_delta = 0)
        # If net_delta is +0.5, we need to short 50 shares (net_delta * 100)
        # If net_delta is -0.5, we need to long 50 shares
        
        target_hedge_shares = -net_delta * 100.0  # Contract multiplier
        
        # Calculate adjustment needed (difference from current position)
        hedge_delta = target_hedge_shares - current_hedge_shares
        
        # Round to nearest share
        hedge_delta = round(hedge_delta)
        
        # Apply minimum hedge size
        if abs(hedge_delta) < self.config.min_hedge_shares:
            return 0.0
        
        return hedge_delta
    
    def execute_hedge(
        self,
        multi_leg_id: str,
        symbol: str,
        net_delta: float,
        current_price: float,
        current_bar: int,
    ) -> tuple[bool, str, float]:
        """
        Execute delta hedge by buying/selling underlying shares.
        
        Returns:
            (success, reason, shares_traded)
        """
        if not self.config.enabled:
            return False, "Hedging disabled", 0.0
        
        # Get or create hedge position
        if multi_leg_id not in self.hedge_positions:
            self.hedge_positions[multi_leg_id] = HedgePosition(
                multi_leg_id=multi_leg_id,
                symbol=symbol,
            )
        
        hedge_pos = self.hedge_positions[multi_leg_id]
        
        # Check daily guardrails
        current_date = datetime.now().strftime("%Y-%m-%d")
        if current_date != self.current_day:
            # Reset daily counters
            self.daily_hedge_trades.clear()
            self.daily_hedge_notional.clear()
            self.current_day = current_date
        
        trades_today = self.daily_hedge_trades.get(symbol, 0)
        notional_today = self.daily_hedge_notional.get(symbol, 0.0)
        
        if trades_today >= self.config.max_hedge_trades_per_day:
            return False, f"Daily hedge trade limit reached: {trades_today}/{self.config.max_hedge_trades_per_day}", 0.0
        
        # Calculate hedge quantity
        hedge_shares = self.calculate_hedge_quantity(net_delta, hedge_pos.hedge_shares)
        
        if abs(hedge_shares) < self.config.min_hedge_shares:
            return False, f"Hedge quantity < {self.config.min_hedge_shares} shares (got {abs(hedge_shares):.2f})", 0.0
        
        # Check notional limit
        hedge_notional = abs(hedge_shares) * current_price
        if notional_today + hedge_notional > self.config.max_hedge_notional_per_day:
            return False, f"Daily hedge notional limit would be exceeded: ${notional_today:.2f} + ${hedge_notional:.2f} > ${self.config.max_hedge_notional_per_day:.2f}", 0.0
        
        # Determine side
        if hedge_shares > 0:
            side_str = "BUY"
            side_value = 1
        else:
            side_str = "SELL"
            side_value = -1
        
        logger.info(
            f"🔄 [DeltaHedge] {multi_leg_id}: "
            f"Hedging {side_str} {abs(hedge_shares):.2f} shares @ ${current_price:.2f} "
            f"(net_delta={net_delta:.3f}, current_hedge={hedge_pos.hedge_shares:.2f})"
        )
        
        # Execute hedge trade
        success = False
        actual_shares = 0.0
        fill_price = current_price
        
        if self.broker_client:
            try:
                from core.live.types import OrderSide, OrderType, TimeInForce
                
                # Submit order
                order = self.broker_client.submit_order(
                    symbol=symbol,
                    side=OrderSide.BUY if hedge_shares > 0 else OrderSide.SELL,
                    quantity=abs(hedge_shares),
                    order_type=OrderType.MARKET,
                    time_in_force=TimeInForce.DAY,
                    current_price=current_price,
                )
                
                if order and order.status.value in ["filled", "partially_filled"]:
                    success = True
                    actual_shares = order.filled_quantity * side_value
                    fill_price = order.filled_price if order.filled_price > 0 else current_price
                    logger.info(
                        f"✅ [DeltaHedge] {multi_leg_id}: Hedge executed: "
                        f"{side_str} {abs(actual_shares):.2f} shares @ ${fill_price:.2f}"
                    )
                else:
                    logger.warning(
                        f"⚠️ [DeltaHedge] {multi_leg_id}: Hedge order not filled: {order.status if order else 'None'}"
                    )
            except Exception as e:
                logger.error(f"❌ [DeltaHedge] {multi_leg_id}: Hedge execution failed: {e}", exc_info=True)
        else:
            # Synthetic execution (for simulation)
            success = True
            actual_shares = hedge_shares
            fill_price = current_price
            logger.info(
                f"📊 [DeltaHedge] {multi_leg_id}: Synthetic hedge: "
                f"{side_str} {abs(actual_shares):.2f} shares @ ${fill_price:.2f}"
            )
        
        if success:
            # Update hedge position with proper average price calculation
            old_hedge_shares = hedge_pos.hedge_shares
            old_avg_price = hedge_pos.hedge_avg_price
            
            # Calculate realized P&L if closing/reversing position
            if old_hedge_shares != 0.0:
                # If reversing direction, realize P&L on the closed portion
                if (old_hedge_shares > 0 and actual_shares < 0) or (old_hedge_shares < 0 and actual_shares > 0):
                    # Closing or reversing position - realize P&L
                    shares_closed = min(abs(old_hedge_shares), abs(actual_shares))
                    realized_pnl = (fill_price - old_avg_price) * shares_closed * (1.0 if old_hedge_shares > 0 else -1.0)
                    hedge_pos.hedge_realized_pnl += realized_pnl
            
            # Update position
            new_total_shares = old_hedge_shares + actual_shares
            
            # Calculate new average price (weighted average)
            if old_hedge_shares == 0.0:
                # First hedge - use fill price
                hedge_pos.hedge_avg_price = fill_price
            elif abs(new_total_shares) > 0.01:
                # Weighted average: (old_shares * old_avg + new_shares * fill_price) / total_shares
                total_cost = (abs(old_hedge_shares) * old_avg_price) + (abs(actual_shares) * fill_price)
                hedge_pos.hedge_avg_price = total_cost / abs(new_total_shares)
            else:
                # Position went flat - keep last avg price for reference
                hedge_pos.hedge_avg_price = old_avg_price
            
            hedge_pos.hedge_shares = new_total_shares
            hedge_pos.last_hedge_price = fill_price
            hedge_pos.last_hedge_time = datetime.now()
            hedge_pos.last_hedge_bar = current_bar
            hedge_pos.last_net_delta = net_delta
            
            hedge_cost = abs(actual_shares) * fill_price
            hedge_pos.total_hedge_cost += hedge_cost
            hedge_pos.hedge_count += 1
            hedge_pos.total_shares_traded += abs(actual_shares)
            
            # Update daily counters
            self.daily_hedge_trades[symbol] = self.daily_hedge_trades.get(symbol, 0) + 1
            self.daily_hedge_notional[symbol] = self.daily_hedge_notional.get(symbol, 0.0) + hedge_notional
            
            logger.info(
                f"📊 [DeltaHedge] {multi_leg_id}: Updated hedge position: "
                f"{old_hedge_shares:.2f} → {hedge_pos.hedge_shares:.2f} shares @ avg ${hedge_pos.hedge_avg_price:.2f}, "
                f"cost=${hedge_cost:.2f}, realized_pnl=${hedge_pos.hedge_realized_pnl:.2f} "
                f"(trades_today={self.daily_hedge_trades.get(symbol, 0)})"
            )
        
        return success, f"Hedge executed: {side_str} {abs(actual_shares):.2f} shares", actual_shares
    
    def check_orphan_hedges(
        self,
        current_bar: int,
        active_multi_leg_ids: set[str],
    ) -> List[tuple[str, str]]:
        """
        Check for orphan hedges (hedge positions without corresponding options).
        
        Returns:
            List of (multi_leg_id, reason) tuples for orphan hedges that need flattening
        """
        orphans = []
        
        for multi_leg_id, hedge_pos in self.hedge_positions.items():
            if multi_leg_id in active_multi_leg_ids:
                # Options still exist, reset orphan counter
                self.orphan_hedge_bars[multi_leg_id] = 0
                continue
            
            # Options closed but hedge remains
            if abs(hedge_pos.hedge_shares) > 0.01:
                bars_orphan = self.orphan_hedge_bars.get(multi_leg_id, 0) + 1
                self.orphan_hedge_bars[multi_leg_id] = bars_orphan
                
                if bars_orphan >= self.config.max_orphan_hedge_bars:
                    orphans.append((
                        multi_leg_id,
                        f"Orphan hedge: {bars_orphan} bars without options (limit: {self.config.max_orphan_hedge_bars})"
                    ))
        
        return orphans
    
    def update_hedge_pnl(
        self,
        multi_leg_id: str,
        current_price: float,
    ) -> float:
        """
        Update unrealized P&L from hedging using average price.
        
        Unrealized P&L = (current_price - hedge_avg_price) * hedge_shares
        
        Returns:
            Current unrealized hedge P&L (does not include realized P&L)
        """
        if multi_leg_id not in self.hedge_positions:
            return 0.0
        
        hedge_pos = self.hedge_positions[multi_leg_id]
        
        if abs(hedge_pos.hedge_shares) < 0.01:
            hedge_pos.hedge_unrealized_pnl = 0.0
            return 0.0
        
        # Calculate unrealized P&L from average price
        # If we're long shares and price > avg_price, we profit
        # If we're short shares and price < avg_price, we profit
        price_diff = current_price - hedge_pos.hedge_avg_price
        hedge_pos.hedge_unrealized_pnl = price_diff * hedge_pos.hedge_shares
        
        return hedge_pos.hedge_unrealized_pnl
    
    def get_total_hedge_pnl(self, multi_leg_id: str) -> float:
        """
        Get total hedge P&L (realized + unrealized) for a position.
        
        Returns:
            Total hedge P&L
        """
        if multi_leg_id not in self.hedge_positions:
            return 0.0
        
        hedge_pos = self.hedge_positions[multi_leg_id]
        return hedge_pos.hedge_realized_pnl + hedge_pos.hedge_unrealized_pnl
    
    def get_hedge_position(self, multi_leg_id: str) -> Optional[HedgePosition]:
        """Get hedge position for a multi-leg position."""
        return self.hedge_positions.get(multi_leg_id)
    
    def remove_hedge_position(
        self,
        multi_leg_id: str,
        current_price: Optional[float] = None,
        symbol: Optional[str] = None,
    ) -> None:
        """
        Remove hedge position when options position is closed.
        
        If hedge position is still open, realize remaining P&L and optionally flatten.
        """
        if multi_leg_id not in self.hedge_positions:
            return
        
        hedge_pos = self.hedge_positions[multi_leg_id]
        
        # Close hedge position if still open
        if abs(hedge_pos.hedge_shares) > 0.01:
            logger.info(
                f"🔄 [DeltaHedge] {multi_leg_id}: Flattening hedge position: "
                f"{hedge_pos.hedge_shares:.2f} shares @ avg ${hedge_pos.hedge_avg_price:.2f}"
            )
            
            # Realize remaining P&L
            if current_price is not None:
                final_pnl = (current_price - hedge_pos.hedge_avg_price) * hedge_pos.hedge_shares
                hedge_pos.hedge_realized_pnl += final_pnl
                hedge_pos.hedge_unrealized_pnl = 0.0
                logger.info(
                    f"💰 [DeltaHedge] {multi_leg_id}: Finalized hedge P&L: "
                    f"${final_pnl:.2f} (total realized: ${hedge_pos.hedge_realized_pnl:.2f})"
                )
            
            # Optionally flatten position via broker
            if self.broker_client and symbol and current_price:
                try:
                    from core.live.types import OrderSide, OrderType, TimeInForce
                    
                    # Flatten: sell if long, buy if short
                    flatten_side = OrderSide.SELL if hedge_pos.hedge_shares > 0 else OrderSide.BUY
                    flatten_qty = abs(hedge_pos.hedge_shares)
                    
                    logger.info(
                        f"📤 [DeltaHedge] {multi_leg_id}: Flattening {flatten_qty:.2f} shares "
                        f"({flatten_side.value})"
                    )
                    
                    order = self.broker_client.submit_order(
                        symbol=symbol,
                        side=flatten_side,
                        quantity=flatten_qty,
                        order_type=OrderType.MARKET,
                        time_in_force=TimeInForce.DAY,
                        current_price=current_price,
                    )
                    
                    if order and order.status.value in ["filled", "partially_filled"]:
                        logger.info(
                            f"✅ [DeltaHedge] {multi_leg_id}: Hedge flattened successfully"
                        )
                except Exception as e:
                    logger.error(
                        f"❌ [DeltaHedge] {multi_leg_id}: Failed to flatten hedge: {e}",
                        exc_info=True,
                    )
        
        del self.hedge_positions[multi_leg_id]
        logger.info(f"📊 [DeltaHedge] Removed hedge position: {multi_leg_id}")
    
    
    def get_hedge_statistics(self, multi_leg_id: str) -> Optional[dict]:
        """Get hedging statistics for a position."""
        if multi_leg_id not in self.hedge_positions:
            return None
        
        hedge_pos = self.hedge_positions[multi_leg_id]
        return {
            "multi_leg_id": multi_leg_id,
            "hedge_shares": hedge_pos.hedge_shares,
            "hedge_count": hedge_pos.hedge_count,
            "total_shares_traded": hedge_pos.total_shares_traded,
            "total_hedge_cost": hedge_pos.total_hedge_cost,
            "hedge_realized_pnl": hedge_pos.hedge_realized_pnl,
            "hedge_unrealized_pnl": hedge_pos.hedge_unrealized_pnl,
            "hedge_avg_price": hedge_pos.hedge_avg_price,
            "last_hedge_price": hedge_pos.last_hedge_price,
            "last_hedge_time": hedge_pos.last_hedge_time.isoformat(),
        }

