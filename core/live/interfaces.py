"""Protocol interfaces for data feeds and brokers."""

from __future__ import annotations

from typing import Protocol
from datetime import datetime
from typing import List, Optional

import pandas as pd

from core.live.types import Bar, Order, OrderSide, OrderType, Position, Account, Fill


class DataFeed(Protocol):
    """Protocol for data feed implementations."""
    
    def connect(self) -> bool:
        """Connect to data feed."""
        ...
    
    def subscribe(self, symbols: List[str], preload_bars: int = 60) -> bool:
        """Subscribe to symbols and preload historical bars."""
        ...
    
    def get_next_bar(self, symbol: str, timeout: float = 5.0) -> Optional[Bar]:
        """Get next bar for symbol."""
        ...
    
    def close(self) -> None:
        """Close data feed connection."""
        ...
    
    def get_latest_bars(self, symbol: str, timeframe: str, lookback_n: int) -> pd.DataFrame:
        """
        Get latest N bars for symbol.
        
        Args:
            symbol: Trading symbol
            timeframe: Bar timeframe (e.g., "1Min", "5Min")
            lookback_n: Number of bars to retrieve
            
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        ...
    
    def get_historical_bars(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        """
        Get historical bars for symbol.
        
        Args:
            symbol: Trading symbol
            timeframe: Bar timeframe (e.g., "1Min", "5Min")
            start: Start datetime
            end: End datetime
            
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        ...


class Broker(Protocol):
    """Protocol for broker implementations."""
    
    def get_account(self) -> Account:
        """Get account information."""
        ...
    
    def get_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """Get current positions."""
        ...
    
    def submit_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        order_type: OrderType,
        time_in_force: Optional[str] = None,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
    ) -> Order:
        """Submit an order."""
        ...
    
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get open orders."""
        ...
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        ...
    
    def get_recent_fills(self, symbol: Optional[str] = None, limit: int = 50) -> List[Fill]:
        """Get recent order fills."""
        ...
    
    def close_position(self, symbol: str, quantity: float) -> bool:
        """Close a position."""
        ...

