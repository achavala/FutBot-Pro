from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Deque, Dict, List, Optional

from collections import deque


@dataclass
class Position:
    """Represents an open position."""

    symbol: str
    quantity: float
    entry_price: float
    entry_time: datetime
    current_price: float
    unrealized_pnl: float = 0.0
    regime_at_entry: Optional[str] = None  # Regime type at entry (e.g., "TREND", "COMPRESSION")
    vol_bucket_at_entry: Optional[str] = None  # Volatility level at entry (e.g., "LOW", "MEDIUM", "HIGH")

    def update_price(self, price: float) -> None:
        """Update current price and unrealized PnL."""
        self.current_price = price
        self.unrealized_pnl = (price - self.entry_price) * self.quantity

    @property
    def market_value(self) -> float:
        """Current market value of position."""
        return self.current_price * self.quantity


@dataclass
class Trade:
    """Represents a completed trade."""

    symbol: str
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    pnl_pct: float
    reason: str
    agent: str
    regime_at_entry: Optional[str] = None  # Regime type at entry (e.g., "TREND", "COMPRESSION")
    vol_bucket_at_entry: Optional[str] = None  # Volatility level at entry (e.g., "LOW", "MEDIUM", "HIGH")


class PortfolioManager:
    """Manages portfolio positions, capital, and trade history."""

    def __init__(self, initial_capital: float, symbol: str):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.symbol = symbol
        self.positions: Dict[str, Position] = {}
        self.trade_history: List[Trade] = []
        self.equity_curve: Deque[float] = deque()
        self.pnl_history: Deque[float] = deque()

    def update_position(self, symbol: str, price: float) -> None:
        """Update position with current market price."""
        if symbol in self.positions:
            self.positions[symbol].update_price(price)

    def add_position(
        self, 
        symbol: str, 
        quantity: float, 
        price: float, 
        timestamp: datetime,
        regime_at_entry: Optional[str] = None,
        vol_bucket_at_entry: Optional[str] = None,
    ) -> None:
        """Add or update a position."""
        if symbol in self.positions:
            # Average in
            pos = self.positions[symbol]
            total_cost = (pos.quantity * pos.entry_price) + (quantity * price)
            total_quantity = pos.quantity + quantity
            pos.entry_price = total_cost / total_quantity if total_quantity != 0 else price
            pos.quantity = total_quantity
            pos.update_price(price)
            # Keep original regime/volatility from first entry
        else:
            self.positions[symbol] = Position(
                symbol=symbol, 
                quantity=quantity, 
                entry_price=price, 
                entry_time=timestamp, 
                current_price=price,
                regime_at_entry=regime_at_entry,
                vol_bucket_at_entry=vol_bucket_at_entry,
            )

    def close_position(
        self, 
        symbol: str, 
        price: float, 
        timestamp: datetime, 
        reason: str, 
        agent: str,
        regime_at_entry: Optional[str] = None,
        vol_bucket_at_entry: Optional[str] = None,
    ) -> Optional[Trade]:
        """Close a position and record the trade."""
        if symbol not in self.positions:
            return None

        pos = self.positions[symbol]
        pnl = (price - pos.entry_price) * pos.quantity
        pnl_pct = ((price - pos.entry_price) / pos.entry_price) * 100.0 if pos.entry_price > 0 else 0.0

        # Use stored regime/volatility from position if not provided
        final_regime = regime_at_entry or pos.regime_at_entry
        final_vol = vol_bucket_at_entry or pos.vol_bucket_at_entry

        trade = Trade(
            symbol=symbol,
            entry_time=pos.entry_time,
            exit_time=timestamp,
            entry_price=pos.entry_price,
            exit_price=price,
            quantity=pos.quantity,
            pnl=pnl,
            pnl_pct=pnl_pct,
            reason=reason,
            agent=agent,
            regime_at_entry=final_regime,
            vol_bucket_at_entry=final_vol,
        )

        self.trade_history.append(trade)
        self.current_capital += pnl
        del self.positions[symbol]

        return trade

    def apply_position_delta(
        self, 
        delta: float, 
        price: float, 
        timestamp: datetime,
        regime_at_entry: Optional[str] = None,
        vol_bucket_at_entry: Optional[str] = None,
    ) -> Optional[Trade]:
        """Apply a position delta (positive = buy, negative = sell)."""
        if delta == 0:
            return None

        current_qty = self.positions.get(self.symbol, Position(self.symbol, 0, price, timestamp, price, regime_at_entry=None, vol_bucket_at_entry=None)).quantity
        new_qty = current_qty + delta

        # Close position if crossing zero
        if current_qty > 0 and new_qty <= 0:
            return self.close_position(self.symbol, price, timestamp, "position_reversal", "system", regime_at_entry, vol_bucket_at_entry)
        elif current_qty < 0 and new_qty >= 0:
            return self.close_position(self.symbol, price, timestamp, "position_reversal", "system", regime_at_entry, vol_bucket_at_entry)

        # Update position
        if new_qty != 0:
            self.add_position(self.symbol, delta, price, timestamp, regime_at_entry, vol_bucket_at_entry)
        elif self.symbol in self.positions:
            # Close if going to zero
            return self.close_position(self.symbol, price, timestamp, "position_closed", "system", regime_at_entry, vol_bucket_at_entry)

        return None

    def get_total_value(self, current_price: float) -> float:
        """Get total portfolio value (capital + unrealized PnL)."""
        unrealized = sum(pos.unrealized_pnl for pos in self.positions.values())
        return self.current_capital + unrealized

    def record_equity(self, current_price: float) -> None:
        """Record current equity for equity curve."""
        total_value = self.get_total_value(current_price)
        self.equity_curve.append(total_value)
        if len(self.equity_curve) > 1:
            pnl = self.equity_curve[-1] - self.equity_curve[-2]
            self.pnl_history.append(pnl)

    def get_total_return_pct(self) -> float:
        """Get total return percentage."""
        if not self.equity_curve:
            return 0.0
        current = self.equity_curve[-1]
        return ((current - self.initial_capital) / self.initial_capital) * 100.0

    def get_max_drawdown(self) -> float:
        """Calculate maximum drawdown."""
        if len(self.equity_curve) < 2:
            return 0.0

        peak = self.equity_curve[0]
        max_dd = 0.0

        for value in self.equity_curve:
            if value > peak:
                peak = value
            dd = ((peak - value) / peak) * 100.0 if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd

        return max_dd

    def get_win_rate(self) -> float:
        """Calculate win rate from trade history."""
        if not self.trade_history:
            return 0.0
        wins = sum(1 for trade in self.trade_history if trade.pnl > 0)
        return (wins / len(self.trade_history)) * 100.0

    def get_sharpe_ratio(self, risk_free_rate: float = 0.0) -> float:
        """Calculate Sharpe ratio from PnL history."""
        if len(self.pnl_history) < 2:
            return 0.0

        import numpy as np

        returns = np.array(self.pnl_history) / self.initial_capital
        excess_returns = returns - (risk_free_rate / 252)  # daily risk-free rate
        if excess_returns.std() == 0:
            return 0.0
        return (excess_returns.mean() / excess_returns.std()) * np.sqrt(252)  # annualized

