"""Cached data feed implementation for offline trading."""

from __future__ import annotations

import logging
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Deque, List, Optional

import pandas as pd

from core.live.data_feed import BaseDataFeed
from core.live.types import Bar
from services.cache import BarCache

logger = logging.getLogger(__name__)


class CachedDataFeed(BaseDataFeed):
    """Data feed that uses cached data for offline trading."""

    def __init__(
        self,
        cache_path: Path,
        bar_size: str = "1Min",
        symbols: Optional[List[str]] = None,
    ):
        """
        Initialize cached data feed.

        Args:
            cache_path: Path to cache database
            bar_size: Bar size (e.g., "1Min", "5Min")
            symbols: List of symbols (optional, can be set in subscribe)
        """
        self.cache_path = cache_path
        self.bar_size = bar_size
        self.cache = BarCache(cache_path)
        
        self.subscribed_symbols: List[str] = []
        self.bar_buffers: dict[str, Deque[Bar]] = {}
        self.current_indices: dict[str, int] = {}  # Track current position in cached data
        self.cached_data: dict[str, list] = {}  # Store loaded cached data
        
        self.connected = False
        
        logger.info(f"Cached data feed initialized (bar_size={bar_size})")

    def connect(self) -> bool:
        """Connect to cached data feed."""
        self.connected = True
        logger.info("Connected to cached data feed")
        return True

    def subscribe(self, symbols: List[str], preload_bars: int = 60) -> bool:
        """
        Subscribe to symbols and load cached data.
        
        Args:
            symbols: List of symbols to subscribe to
            preload_bars: Number of bars to preload (default 60)
        """
        if not self.connected:
            logger.error("Cannot subscribe: not connected")
            return False

        self.subscribed_symbols = symbols
        
        for symbol in symbols:
            self.bar_buffers[symbol] = deque(maxlen=500)
            self.current_indices[symbol] = 0
            
            # Load cached data
            logger.info(f"Loading cached data for {symbol}...")
            cached_df = self.cache.load(symbol, self.bar_size)
            
            if cached_df.empty:
                logger.warning(f"No cached data found for {symbol} - generating synthetic bars for simulation")
                # Generate synthetic bars for simulation when cache is empty
                bars_list = self._generate_synthetic_bars(symbol, preload_bars)
                self.cached_data[symbol] = bars_list
                logger.info(f"Generated {len(bars_list)} synthetic bars for {symbol}")
            else:
                # Convert DataFrame to list of Bar objects
                import pandas as pd
                bars_list = []
                for idx, row in cached_df.iterrows():
                    bar_time = idx if isinstance(idx, datetime) else pd.to_datetime(idx)
                    if isinstance(bar_time, pd.Timestamp):
                        bar_time = bar_time.to_pydatetime()
                    
                    bar = Bar(
                        symbol=symbol,
                        timestamp=bar_time,
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        volume=float(row.get("volume", 0)),
                    )
                    bars_list.append(bar)
                
                self.cached_data[symbol] = bars_list
                logger.info(f"Loaded {len(bars_list)} cached bars for {symbol}")
            
            # Preload bars into buffer (works for both cached and synthetic)
            if symbol in self.cached_data and len(self.cached_data[symbol]) > 0:
                bars_list = self.cached_data[symbol]
                bars_to_load = bars_list[-min(preload_bars, len(bars_list)):]
                for bar in bars_to_load:
                    self.bar_buffers[symbol].append(bar)
                logger.info(f"Preloaded {len(bars_to_load)} bars for {symbol} into buffer")

        logger.info(f"Subscribed to symbols: {symbols}")
        return True

    def _generate_synthetic_bars(self, symbol: str, count: int = 500) -> List[Bar]:
        """
        Generate synthetic bars for simulation when no cached data exists.
        
        Args:
            symbol: Trading symbol
            count: Number of bars to generate
            
        Returns:
            List of Bar objects
        """
        import random
        from datetime import datetime, timedelta
        
        # Default prices for common symbols
        default_prices = {
            "QQQ": 400.0,
            "SPY": 450.0,
            "SPX": 4500.0,
            "BTC/USD": 50000.0,
            "ETH/USD": 3000.0,
        }
        
        # Start with default price or random if unknown
        base_price = default_prices.get(symbol, random.uniform(100.0, 500.0))
        current_price = base_price
        
        bars_list = []
        now = datetime.now(timezone.utc)
        
        # Generate bars going backwards in time
        for i in range(count):
            # Random walk: ±0.5% change per bar
            change_pct = random.uniform(-0.005, 0.005)
            new_price = current_price * (1 + change_pct)
            
            # Generate OHLC
            high = max(current_price, new_price) * (1 + abs(random.uniform(0, 0.002)))
            low = min(current_price, new_price) * (1 - abs(random.uniform(0, 0.002)))
            volume = random.uniform(1000000, 10000000)
            
            # Timestamp going backwards
            bar_time = now - timedelta(minutes=count - i)
            
            bar = Bar(
                symbol=symbol,
                timestamp=bar_time,
                open=current_price,
                high=high,
                low=low,
                close=new_price,
                volume=volume,
            )
            bars_list.append(bar)
            current_price = new_price
        
        return bars_list

    def get_next_bar(self, symbol: str, timeout: float = 5.0) -> Optional[Bar]:
        """
        Get next bar from cached data.
        
        Args:
            symbol: Symbol to get bar for
            timeout: Timeout in seconds (not used for cached data)
        """
        if not self.connected:
            logger.debug(f"Data feed not connected for {symbol}")
            return None

        if symbol not in self.subscribed_symbols:
            logger.debug(f"Symbol {symbol} not subscribed")
            return None

        # First, check if we have bars in buffer
        if symbol in self.bar_buffers and len(self.bar_buffers[symbol]) > 0:
            bar = self.bar_buffers[symbol].popleft()
            logger.debug(f"Returning buffered bar for {symbol}: {bar.timestamp}")
            return bar

        # No buffered bars, get next from cached data
        if symbol not in self.cached_data or len(self.cached_data[symbol]) == 0:
            logger.debug(f"No cached data available for {symbol}")
            return None

        # Get next bar from cached data
        current_idx = self.current_indices.get(symbol, 0)
        cached_bars = self.cached_data[symbol]
        
        if current_idx >= len(cached_bars):
            logger.debug(f"Reached end of cached data for {symbol}")
            return None
        
        bar = cached_bars[current_idx]
        self.current_indices[symbol] = current_idx + 1
        
        logger.debug(f"Returning cached bar {current_idx + 1}/{len(cached_bars)} for {symbol}: {bar.timestamp}")
        return bar

    def reset(self, symbol: Optional[str] = None) -> None:
        """
        Reset to beginning of cached data.
        
        Args:
            symbol: Symbol to reset (None = all symbols)
        """
        if symbol:
            self.current_indices[symbol] = 0
            if symbol in self.bar_buffers:
                self.bar_buffers[symbol].clear()
        else:
            for sym in self.subscribed_symbols:
                self.current_indices[sym] = 0
                if sym in self.bar_buffers:
                    self.bar_buffers[sym].clear()
        logger.info(f"Reset cached data feed for {symbol or 'all symbols'}")

    def get_latest_bars(self, symbol: str, timeframe: str, lookback_n: int) -> pd.DataFrame:
        """
        Get latest N bars for symbol from cache.
        
        Args:
            symbol: Trading symbol
            timeframe: Bar timeframe (e.g., "1Min", "5Min")
            lookback_n: Number of bars to retrieve
            
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        try:
            # Load all bars for symbol/timeframe
            df = self.cache.load(symbol, timeframe)
            
            if df.empty:
                logger.warning(f"No cached data found for {symbol} ({timeframe})")
                # Return empty DataFrame with correct structure (DatetimeIndex)
                return pd.DataFrame(columns=["open", "high", "low", "close", "volume"]).set_index(pd.DatetimeIndex([]))
            
            # Get last N bars
            df = df.tail(lookback_n)
            
            # BarCache.load() already returns DataFrame with DatetimeIndex
            # Ensure required columns exist
            required_cols = ["open", "high", "low", "close", "volume"]
            for col in required_cols:
                if col not in df.columns:
                    logger.warning(f"Missing column {col} in cached data for {symbol}")
                    df[col] = 0.0
            
            # Return DataFrame with timestamp as index
            return df[["open", "high", "low", "close", "volume"]]
        except Exception as e:
            logger.error(f"Error loading latest bars for {symbol}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"]).set_index(pd.DatetimeIndex([]))

    def get_historical_bars(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        """
        Get historical bars for symbol from cache.
        
        Args:
            symbol: Trading symbol
            timeframe: Bar timeframe (e.g., "1Min", "5Min")
            start: Start datetime
            end: End datetime
            
        Returns:
            DataFrame with timestamp as index and columns: open, high, low, close, volume
        """
        try:
            # Convert datetime to timestamp (milliseconds since epoch, as BarCache expects)
            # BarCache stores timestamps in milliseconds
            start_ts = int(start.timestamp() * 1000)
            end_ts = int(end.timestamp() * 1000)
            
            # Load bars from cache with time range
            df = self.cache.load(symbol, timeframe, start_ts=start_ts, end_ts=end_ts)
            
            if df.empty:
                logger.warning(f"No cached data found for {symbol} ({timeframe}) between {start} and {end}")
                # Return empty DataFrame with correct structure
                return pd.DataFrame(columns=["open", "high", "low", "close", "volume"]).set_index(pd.DatetimeIndex([]))
            
            # BarCache.load already returns DataFrame with DatetimeIndex
            # Ensure required columns exist
            required_cols = ["open", "high", "low", "close", "volume"]
            for col in required_cols:
                if col not in df.columns:
                    logger.warning(f"Missing column {col} in cached data for {symbol}")
                    df[col] = 0.0
            
            return df[["open", "high", "low", "close", "volume"]]
        except Exception as e:
            logger.error(f"Error loading historical bars for {symbol}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"]).set_index(pd.DatetimeIndex([]))

    def close(self) -> None:
        """Close data feed."""
        self.connected = False
        self.subscribed_symbols = []
        self.bar_buffers.clear()
        self.current_indices.clear()
        self.cached_data.clear()
        logger.info("Cached data feed closed")

