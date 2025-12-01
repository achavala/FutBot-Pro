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


class OptionsPortfolioManager:
    """Manages synthetic options positions separately from stock positions."""

    def __init__(self):
        self.positions: Dict[str, OptionPosition] = {}  # key: option_symbol
        self.trades: List[OptionTrade] = []

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
        return total_pnl


