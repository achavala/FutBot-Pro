from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque
from datetime import datetime
from typing import Deque, List, Optional

from core.live.types import Bar


class BaseDataFeed(ABC):
    """Abstract base class for live data feeds."""

    @abstractmethod
    def connect(self) -> bool:
        """Connect to data feed."""
        pass

    @abstractmethod
    def subscribe(self, symbols: List[str], preload_bars: int = 0) -> bool:
        """Subscribe to symbols."""
        pass

    @abstractmethod
    def get_next_bar(self, symbol: str, timeout: float = 5.0) -> Optional[Bar]:
        """Get next bar for symbol. Returns None if timeout."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close data feed connection."""
        pass


class PollingDataFeed(BaseDataFeed):
    """Polling-based data feed (uses REST API)."""

    def __init__(self, broker_client, poll_interval: float = 60.0):
        self.broker_client = broker_client
        self.poll_interval = poll_interval
        self.subscribed_symbols: List[str] = []
        self.bar_buffers: dict[str, Deque[Bar]] = {}
        self.last_bar_times: dict[str, datetime] = {}
        self.connected = False

    def connect(self) -> bool:
        """Connect to data feed."""
        self.connected = True
        return True

    def subscribe(self, symbols: List[str]) -> bool:
        """Subscribe to symbols."""
        self.subscribed_symbols = symbols
        for symbol in symbols:
            self.bar_buffers[symbol] = deque(maxlen=500)
        return True

    def get_next_bar(self, symbol: str, timeout: float = 5.0) -> Optional[Bar]:
        """Get next bar by polling broker API."""
        import time

        # TODO: Implement actual polling from broker API
        # For now, return None (stub)
        time.sleep(0.1)  # Simulate network delay
        return None

    def close(self) -> None:
        """Close data feed."""
        self.connected = False
        self.subscribed_symbols = []
        self.bar_buffers.clear()


class MockDataFeed(BaseDataFeed):
    """Mock data feed for testing (generates synthetic bars)."""

    def __init__(self, initial_price: float = 100.0):
        self.initial_price = initial_price
        self.subscribed_symbols: List[str] = []
        self.bar_buffers: dict[str, Deque[Bar]] = {}
        self.current_prices: dict[str, float] = {}
        self.bar_count: dict[str, int] = {}
        self.connected = False

    def connect(self) -> bool:
        """Connect to mock feed."""
        self.connected = True
        return True

    def subscribe(self, symbols: List[str], preload_bars: int = 0) -> bool:
        """Subscribe to symbols."""
        self.subscribed_symbols = symbols
        for symbol in symbols:
            self.bar_buffers[symbol] = deque(maxlen=500)
            self.current_prices[symbol] = self.initial_price
            self.bar_count[symbol] = 0
        return True

    def get_next_bar(self, symbol: str, timeout: float = 5.0) -> Optional[Bar]:
        """Generate next mock bar."""
        if symbol not in self.subscribed_symbols:
            return None

        import random
        from datetime import datetime, timedelta

        # Generate synthetic bar with random walk
        current_price = self.current_prices[symbol]
        change_pct = random.uniform(-0.02, 0.02)  # ±2% change
        new_price = current_price * (1 + change_pct)

        high = max(current_price, new_price) * (1 + abs(random.uniform(0, 0.01)))
        low = min(current_price, new_price) * (1 - abs(random.uniform(0, 0.01)))
        volume = random.uniform(1000, 10000)

        bar = Bar(
            symbol=symbol,
            timestamp=datetime.now() - timedelta(minutes=500 - self.bar_count[symbol]),
            open=current_price,
            high=high,
            low=low,
            close=new_price,
            volume=volume,
        )

        self.current_prices[symbol] = new_price
        self.bar_count[symbol] += 1
        self.bar_buffers[symbol].append(bar)

        return bar

    def close(self) -> None:
        """Close mock feed."""
        self.connected = False
        self.subscribed_symbols = []
        self.bar_buffers.clear()

