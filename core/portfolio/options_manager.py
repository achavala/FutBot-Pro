"""Options portfolio manager for tracking synthetic options positions and trades."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

import logging

logger = logging.getLogger(__name__)


@dataclass
class OptionPosition:
    """Represents an open synthetic options position."""

    symbol: str  # Underlying symbol (e.g., "QQQ")
    option_symbol: str  # Synthetic option identifier (e.g., "QQQ_CALL_ATM_0DTE")
    option_type: str  # "call" | "put"
    strike: float  # Strike price
    expiration: datetime  # Expiration date/time
    quantity: float  # Number of contracts (positive = long, negative = short)
    entry_price: float  # Premium paid/received per contract
    entry_time: datetime
    current_price: float  # Current premium (synthetic)
    underlying_price: float  # Current underlying price
    delta: float  # Synthetic delta
    theta: float  # Synthetic theta (time decay per day)
    iv: float  # Implied volatility estimate
    unrealized_pnl: float = 0.0
    regime_at_entry: Optional[str] = None
    vol_bucket_at_entry: Optional[str] = None

    def update_price(
        self,
        underlying_price: float,
        option_price: float,
        delta: float,
        theta: float,
        iv: float,
    ) -> None:
        """Update position with current prices and Greeks."""
        self.underlying_price = underlying_price
        self.current_price = option_price
        self.delta = delta
        self.theta = theta
        self.iv = iv

        # Calculate unrealized P&L
        # For long options: (current_price - entry_price) * quantity * 100
        # For short options: (entry_price - current_price) * quantity * 100
        # Options contracts are typically 100 shares per contract
        contract_multiplier = 100.0
        if self.quantity > 0:  # Long
            self.unrealized_pnl = (option_price - self.entry_price) * abs(self.quantity) * contract_multiplier
        else:  # Short
            self.unrealized_pnl = (self.entry_price - option_price) * abs(self.quantity) * contract_multiplier

    @property
    def days_to_expiry(self) -> float:
        """Calculate days to expiration."""
        if self.expiration <= datetime.now():
            return 0.0
        delta = self.expiration - datetime.now()
        return delta.total_seconds() / (24 * 3600)

    @property
    def is_expired(self) -> bool:
        """Check if option has expired."""
        return datetime.now() >= self.expiration


@dataclass
class OptionTrade:
    """Represents a completed synthetic options trade."""

    symbol: str
    option_symbol: str
    option_type: str
    strike: float
    expiration: datetime
    quantity: float  # Number of contracts
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: datetime
    pnl: float  # Total P&L in dollars
    pnl_pct: float  # P&L as percentage of entry premium
    reason: str
    agent: str
    delta_at_entry: float
    iv_at_entry: float
    regime_at_entry: Optional[str] = None
    vol_bucket_at_entry: Optional[str] = None

    @property
    def duration_minutes(self) -> float:
        """Calculate trade duration in minutes."""
        delta = self.exit_time - self.entry_time
        return delta.total_seconds() / 60.0


@dataclass
class LegFill:
    """Represents a fill for one leg of a multi-leg trade."""
    
    leg_type: str  # "call" or "put"
    option_symbol: str  # Full option symbol
    strike: float
    quantity: int  # Number of contracts filled
    fill_price: float  # Price per contract
    fill_time: datetime
    order_id: Optional[str] = None  # Broker order ID
    status: str = "filled"  # "pending", "partially_filled", "filled", "rejected"
    
    @property
    def total_cost(self) -> float:
        """Calculate total cost for this leg (quantity * price * 100)."""
        return self.quantity * self.fill_price * 100.0


@dataclass
class MultiLegPosition:
    """Represents a multi-leg options position (straddle or strangle)."""
    
    symbol: str  # Underlying symbol
    trade_type: str  # "straddle" or "strangle"
    direction: str  # "long" or "short"
    multi_leg_id: str  # Unique identifier for this multi-leg position
    
    # Leg 1 (Call)
    call_option_symbol: str
    call_strike: float
    call_quantity: int  # Number of contracts
    call_entry_price: float
    call_current_price: float
    call_delta: float
    call_theta: float
    call_iv: float
    
    # Leg 2 (Put)
    put_option_symbol: str
    put_strike: float
    put_quantity: int
    put_entry_price: float
    put_current_price: float
    put_delta: float
    put_theta: float
    put_iv: float
    
    expiration: datetime
    entry_time: datetime
    underlying_price: float
    
    # Fill tracking
    call_fill: Optional[LegFill] = None
    put_fill: Optional[LegFill] = None
    both_legs_filled: bool = False
    
    # Combined metrics
    total_credit: float = 0.0  # Net credit received (for short positions)
    total_debit: float = 0.0  # Net debit paid (for long positions)
    combined_unrealized_pnl: float = 0.0
    regime_at_entry: Optional[str] = None
    vol_bucket_at_entry: Optional[str] = None
    
    def update_prices(
        self,
        underlying_price: float,
        call_price: float,
        put_price: float,
        call_delta: float,
        put_delta: float,
        call_theta: float,
        put_theta: float,
        call_iv: float,
        put_iv: float,
    ) -> None:
        """Update position with current prices and Greeks."""
        self.underlying_price = underlying_price
        self.call_current_price = call_price
        self.put_current_price = put_price
        self.call_delta = call_delta
        self.put_delta = put_delta
        self.call_theta = call_theta
        self.put_theta = put_theta
        self.call_iv = call_iv
        self.put_iv = put_iv
        
        # Calculate combined unrealized P&L
        contract_multiplier = 100.0
        
        # Call leg P&L
        if self.direction == "long":
            call_pnl = (call_price - self.call_entry_price) * self.call_quantity * contract_multiplier
            put_pnl = (put_price - self.put_entry_price) * self.put_quantity * contract_multiplier
        else:  # short
            call_pnl = (self.call_entry_price - call_price) * self.call_quantity * contract_multiplier
            put_pnl = (self.put_entry_price - put_price) * self.put_quantity * contract_multiplier
        
        self.combined_unrealized_pnl = call_pnl + put_pnl
    
    @property
    def days_to_expiry(self) -> float:
        """Calculate days to expiration."""
        if self.expiration <= datetime.now():
            return 0.0
        delta = self.expiration - datetime.now()
        return delta.total_seconds() / (24 * 3600)
    
    @property
    def is_expired(self) -> bool:
        """Check if position has expired."""
        return datetime.now() >= self.expiration
    
    @property
    def net_premium(self) -> float:
        """Get net premium (credit for short, debit for long)."""
        if self.direction == "short":
            return self.total_credit
        else:
            return -self.total_debit  # Negative because it's a cost
    
    @property
    def net_delta(self) -> float:
        """
        Calculate net delta of the multi-leg position.
        
        For long strangles (Gamma Scalper):
        - Call delta is positive (e.g., +0.25)
        - Put delta is negative (e.g., -0.25)
        - Net delta = (call_delta * call_quantity) + (put_delta * put_quantity)
        
        For short straddles (Theta Harvester):
        - Call delta is positive, but we're short (negative contribution)
        - Put delta is negative, but we're short (positive contribution)
        - Net delta = -(call_delta * call_quantity) - (put_delta * put_quantity)
        """
        if self.direction == "long":
            # Long strangle: add deltas
            return (self.call_delta * self.call_quantity) + (self.put_delta * self.put_quantity)
        else:
            # Short straddle: negate deltas
            return -((self.call_delta * self.call_quantity) + (self.put_delta * self.put_quantity))


@dataclass
class MultiLegTrade:
    """Represents a completed multi-leg options trade."""
    
    symbol: str
    trade_type: str  # "straddle" or "strangle"
    direction: str  # "long" or "short"
    multi_leg_id: str
    
    # Entry
    call_option_symbol: str
    call_strike: float
    put_option_symbol: str
    put_strike: float
    call_quantity: int
    put_quantity: int
    call_entry_price: float
    put_entry_price: float
    expiration: datetime
    entry_time: datetime
    
    # Exit
    call_exit_price: float
    put_exit_price: float
    exit_time: datetime
    
    # Combined P&L
    combined_pnl: float  # Total P&L across both legs
    combined_pnl_pct: float  # P&L as percentage of net premium
    net_premium: float  # Net credit/debit at entry
    
    reason: str
    agent: str
    regime_at_entry: Optional[str] = None
    vol_bucket_at_entry: Optional[str] = None
    
    @property
    def duration_minutes(self) -> float:
        """Calculate trade duration in minutes."""
        delta = self.exit_time - self.entry_time
        return delta.total_seconds() / 60.0


class OptionsPortfolioManager:
    """Manages synthetic options positions separately from stock positions."""

    def __init__(self):
        self.positions: Dict[str, OptionPosition] = {}  # key: option_symbol
        self.multi_leg_positions: Dict[str, MultiLegPosition] = {}  # key: multi_leg_id
        self.trades: List[OptionTrade] = []
        self.multi_leg_trades: List[MultiLegTrade] = []

    def add_position(
        self,
        symbol: str,
        option_symbol: str,
        option_type: str,
        strike: float,
        expiration: datetime,
        quantity: float,
        entry_price: float,
        entry_time: datetime,
        underlying_price: float,
        delta: float,
        theta: float,
        iv: float,
        regime_at_entry: Optional[str] = None,
        vol_bucket_at_entry: Optional[str] = None,
    ) -> OptionPosition:
        """Add or update an options position."""
        if option_symbol in self.positions:
            # Update existing position (averaging in)
            pos = self.positions[option_symbol]
            total_cost = (pos.quantity * pos.entry_price) + (quantity * entry_price)
            total_quantity = pos.quantity + quantity
            pos.entry_price = total_cost / total_quantity if total_quantity != 0 else entry_price
            pos.quantity = total_quantity
            pos.update_price(underlying_price, entry_price, delta, theta, iv)
            # Keep original regime/volatility from first entry
        else:
            # New position
            self.positions[option_symbol] = OptionPosition(
                symbol=symbol,
                option_symbol=option_symbol,
                option_type=option_type,
                strike=strike,
                expiration=expiration,
                quantity=quantity,
                entry_price=entry_price,
                entry_time=entry_time,
                current_price=entry_price,
                underlying_price=underlying_price,
                delta=delta,
                theta=theta,
                iv=iv,
                regime_at_entry=regime_at_entry,
                vol_bucket_at_entry=vol_bucket_at_entry,
            )
        return self.positions[option_symbol]

    def close_position(
        self,
        option_symbol: str,
        exit_price: float,
        exit_time: datetime,
        underlying_price: float,
        reason: str,
        agent: str = "system",
    ) -> Optional[OptionTrade]:
        """Close an options position."""
        if option_symbol not in self.positions:
            return None

        pos = self.positions[option_symbol]
        if pos.quantity == 0:
            return None

        # Calculate P&L
        contract_multiplier = 100.0
        if pos.quantity > 0:  # Long
            pnl = (exit_price - pos.entry_price) * abs(pos.quantity) * contract_multiplier
        else:  # Short
            pnl = (pos.entry_price - exit_price) * abs(pos.quantity) * contract_multiplier

        pnl_pct = ((exit_price - pos.entry_price) / pos.entry_price * 100.0) if pos.entry_price > 0 else 0.0

        # Create trade record
        trade = OptionTrade(
            symbol=pos.symbol,
            option_symbol=option_symbol,
            option_type=pos.option_type,
            strike=pos.strike,
            expiration=pos.expiration,
            quantity=pos.quantity,
            entry_price=pos.entry_price,
            exit_price=exit_price,
            entry_time=pos.entry_time,
            exit_time=exit_time,
            pnl=pnl,
            pnl_pct=pnl_pct,
            reason=reason,
            agent=agent,
            delta_at_entry=pos.delta,
            iv_at_entry=pos.iv,
            regime_at_entry=pos.regime_at_entry,
            vol_bucket_at_entry=pos.vol_bucket_at_entry,
        )

        self.trades.append(trade)
        del self.positions[option_symbol]

        return trade

    def update_position(
        self,
        option_symbol: str,
        underlying_price: float,
        option_price: float,
        delta: float,
        theta: float,
        iv: float,
    ) -> None:
        """Update position prices and Greeks."""
        if option_symbol in self.positions:
            self.positions[option_symbol].update_price(underlying_price, option_price, delta, theta, iv)

    def get_position(self, option_symbol: str) -> Optional[OptionPosition]:
        """Get a position by option symbol."""
        return self.positions.get(option_symbol)

    def get_all_positions(self) -> List[OptionPosition]:
        """Get all open positions."""
        return list(self.positions.values())

    def get_round_trip_trades(
        self,
        symbol: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[OptionTrade]:
        """Get completed round-trip trades with optional filtering."""
        trades = self.trades

        if symbol:
            trades = [t for t in trades if t.symbol == symbol]

        if start_date:
            trades = [t for t in trades if t.entry_time >= start_date]

        if end_date:
            trades = [t for t in trades if t.exit_time <= end_date]

        # Sort by exit time (most recent first)
        trades.sort(key=lambda t: t.exit_time, reverse=True)

        return trades[:limit]

    def get_total_value(self, underlying_prices: Dict[str, float]) -> float:
        """Get total portfolio value (unrealized P&L for all positions)."""
        total_pnl = 0.0
        for pos in self.positions.values():
            if pos.symbol in underlying_prices:
                # Position P&L is already calculated in update_price
                total_pnl += pos.unrealized_pnl
        
        # Add multi-leg positions P&L
        for ml_pos in self.multi_leg_positions.values():
            if ml_pos.symbol in underlying_prices:
                total_pnl += ml_pos.combined_unrealized_pnl
        
        return total_pnl
    
    def add_multi_leg_position(
        self,
        symbol: str,
        trade_type: str,  # "straddle" or "strangle"
        direction: str,  # "long" or "short"
        multi_leg_id: str,
        call_option_symbol: str,
        call_strike: float,
        call_quantity: int,
        call_entry_price: float,
        call_delta: float,
        call_theta: float,
        call_iv: float,
        put_option_symbol: str,
        put_strike: float,
        put_quantity: int,
        put_entry_price: float,
        put_delta: float,
        put_theta: float,
        put_iv: float,
        expiration: datetime,
        entry_time: datetime,
        underlying_price: float,
        call_fill: Optional[LegFill] = None,
        put_fill: Optional[LegFill] = None,
        regime_at_entry: Optional[str] = None,
        vol_bucket_at_entry: Optional[str] = None,
    ) -> MultiLegPosition:
        """Add a multi-leg position (straddle or strangle)."""
        contract_multiplier = 100.0
        
        # Calculate net premium (credit for short, debit for long)
        call_cost = call_entry_price * call_quantity * contract_multiplier
        put_cost = put_entry_price * put_quantity * contract_multiplier
        
        if direction == "short":
            # Selling premium = receiving credit
            total_credit = call_cost + put_cost
            total_debit = 0.0
        else:
            # Buying premium = paying debit
            total_debit = call_cost + put_cost
            total_credit = 0.0
        
        ml_pos = MultiLegPosition(
            symbol=symbol,
            trade_type=trade_type,
            direction=direction,
            multi_leg_id=multi_leg_id,
            call_option_symbol=call_option_symbol,
            call_strike=call_strike,
            call_quantity=call_quantity,
            call_entry_price=call_entry_price,
            call_current_price=call_entry_price,
            call_delta=call_delta,
            call_theta=call_theta,
            call_iv=call_iv,
            put_option_symbol=put_option_symbol,
            put_strike=put_strike,
            put_quantity=put_quantity,
            put_entry_price=put_entry_price,
            put_current_price=put_entry_price,
            put_delta=put_delta,
            put_theta=put_theta,
            put_iv=put_iv,
            expiration=expiration,
            entry_time=entry_time,
            underlying_price=underlying_price,
            call_fill=call_fill,
            put_fill=put_fill,
            both_legs_filled=(call_fill is not None and put_fill is not None),
            total_credit=total_credit,
            total_debit=total_debit,
            regime_at_entry=regime_at_entry,
            vol_bucket_at_entry=vol_bucket_at_entry,
        )
        
        self.multi_leg_positions[multi_leg_id] = ml_pos
        return ml_pos
    
    def update_multi_leg_fill(
        self,
        multi_leg_id: str,
        leg_type: str,  # "call" or "put"
        fill: LegFill,
    ) -> Optional[MultiLegPosition]:
        """Update a multi-leg position with a leg fill."""
        if multi_leg_id not in self.multi_leg_positions:
            return None
        
        ml_pos = self.multi_leg_positions[multi_leg_id]
        
        if leg_type == "call":
            ml_pos.call_fill = fill
        elif leg_type == "put":
            ml_pos.put_fill = fill
        
        # Check if both legs are filled
        ml_pos.both_legs_filled = (
            ml_pos.call_fill is not None 
            and ml_pos.put_fill is not None
            and ml_pos.call_fill.status == "filled"
            and ml_pos.put_fill.status == "filled"
        )
        
        return ml_pos
    
    def close_multi_leg_position(
        self,
        multi_leg_id: str,
        call_exit_price: float,
        put_exit_price: float,
        exit_time: datetime,
        underlying_price: float,
        reason: str,
        agent: str = "system",
    ) -> Optional[MultiLegTrade]:
        """Close a multi-leg position."""
        if multi_leg_id not in self.multi_leg_positions:
            return None
        
        ml_pos = self.multi_leg_positions[multi_leg_id]
        
        # Calculate combined P&L
        contract_multiplier = 100.0
        
        if ml_pos.direction == "long":
            # Long: profit if exit > entry
            call_pnl = (call_exit_price - ml_pos.call_entry_price) * ml_pos.call_quantity * contract_multiplier
            put_pnl = (put_exit_price - ml_pos.put_entry_price) * ml_pos.put_quantity * contract_multiplier
        else:
            # Short: profit if entry > exit
            call_pnl = (ml_pos.call_entry_price - call_exit_price) * ml_pos.call_quantity * contract_multiplier
            put_pnl = (ml_pos.put_entry_price - put_exit_price) * ml_pos.put_quantity * contract_multiplier
        
        combined_pnl = call_pnl + put_pnl
        
        # Calculate P&L as percentage of net premium
        net_premium = ml_pos.net_premium
        combined_pnl_pct = (combined_pnl / net_premium * 100.0) if net_premium > 0 else 0.0
        
        # Create trade record
        trade = MultiLegTrade(
            symbol=ml_pos.symbol,
            trade_type=ml_pos.trade_type,
            direction=ml_pos.direction,
            multi_leg_id=multi_leg_id,
            call_option_symbol=ml_pos.call_option_symbol,
            call_strike=ml_pos.call_strike,
            put_option_symbol=ml_pos.put_option_symbol,
            put_strike=ml_pos.put_strike,
            call_quantity=ml_pos.call_quantity,
            put_quantity=ml_pos.put_quantity,
            call_entry_price=ml_pos.call_entry_price,
            put_entry_price=ml_pos.put_entry_price,
            call_exit_price=call_exit_price,
            put_exit_price=put_exit_price,
            expiration=ml_pos.expiration,
            entry_time=ml_pos.entry_time,
            exit_time=exit_time,
            combined_pnl=combined_pnl,
            combined_pnl_pct=combined_pnl_pct,
            net_premium=net_premium,
            reason=reason,
            agent=agent,
            regime_at_entry=ml_pos.regime_at_entry,
            vol_bucket_at_entry=ml_pos.vol_bucket_at_entry,
        )
        
        self.multi_leg_trades.append(trade)
        del self.multi_leg_positions[multi_leg_id]
        
        return trade
    
    def get_multi_leg_position(self, multi_leg_id: str) -> Optional[MultiLegPosition]:
        """Get a multi-leg position by ID."""
        return self.multi_leg_positions.get(multi_leg_id)
    
    def get_all_multi_leg_positions(self) -> List[MultiLegPosition]:
        """Get all open multi-leg positions."""
        return list(self.multi_leg_positions.values())


