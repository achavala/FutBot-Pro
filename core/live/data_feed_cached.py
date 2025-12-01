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
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ):
        """
        Initialize cached data feed.

        Args:
            cache_path: Path to cache database
            bar_size: Bar size (e.g., "1Min", "5Min")
            symbols: List of symbols (optional, can be set in subscribe)
            start_date: Start from specific datetime (for historical replay)
            end_date: End at specific datetime (for time-windowed simulation)
        """
        self.cache_path = cache_path
        self.bar_size = bar_size
        self.cache = BarCache(cache_path)
        self.start_date = start_date
        self.end_date = end_date
        
        self.subscribed_symbols: List[str] = []
        self.bar_buffers: dict[str, Deque[Bar]] = {}
        self.current_indices: dict[str, int] = {}  # Track current position in cached data
        self.cached_data: dict[str, list] = {}  # Store loaded cached data
        self.synthetic_enabled: bool = True  # Enable synthetic bar generation as fallback
        self.strict_data_mode: bool = False  # If True, fail hard when cached data is missing (production safety)
        
        self.connected = False
        
        if start_date and end_date:
            logger.info(f"Cached data feed initialized (bar_size={bar_size}, start_date={start_date}, end_date={end_date})")
        elif start_date:
            logger.info(f"Cached data feed initialized (bar_size={bar_size}, start_date={start_date})")
        else:
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
            
            # If start_date or end_date is specified, load data in that range
            if self.start_date or self.end_date:
                # Ensure timezone-aware timestamps for accurate conversion
                start_date_utc = self.start_date
                end_date_utc = self.end_date
                if start_date_utc and start_date_utc.tzinfo is None:
                    start_date_utc = start_date_utc.replace(tzinfo=timezone.utc)
                if end_date_utc and end_date_utc.tzinfo is None:
                    end_date_utc = end_date_utc.replace(tzinfo=timezone.utc)
                
                start_ts = int(start_date_utc.timestamp() * 1000) if start_date_utc else None
                end_ts = int(end_date_utc.timestamp() * 1000) if end_date_utc else None
                
                # Normalize timeframe for cache lookup (cache uses lowercase "1min", not "1Min")
                cache_timeframe = self.bar_size.lower().replace("minute", "min")
                logger.info(f"📅 [CachedDataFeed] Querying cache: symbol={symbol}, timeframe={cache_timeframe} (normalized from {self.bar_size}), start_ts={start_ts}, end_ts={end_ts}")
                cached_df = self.cache.load(symbol, cache_timeframe, start_ts=start_ts, end_ts=end_ts)
                
                if self.start_date and self.end_date:
                    logger.info(f"📅 [CachedDataFeed] Loading data from {self.start_date} to {self.end_date} for {symbol}")
                elif self.start_date:
                    logger.info(f"📅 [CachedDataFeed] Loading data from {self.start_date} onwards for {symbol}")
                elif self.end_date:
                    logger.info(f"📅 [CachedDataFeed] Loading data up to {self.end_date} for {symbol}")
                
                if cached_df.empty:
                    logger.warning(f"⚠️ [CachedDataFeed] No data found in cache for {symbol} in date range. Checking if data exists without date filter...")
                    # Try loading without date filter to see if data exists
                    cache_timeframe = self.bar_size.lower().replace("minute", "min")
                    test_df = self.cache.load(symbol, cache_timeframe)
                    if not test_df.empty:
                        logger.warning(f"⚠️ [CachedDataFeed] Found {len(test_df)} bars for {symbol} without date filter")
                        logger.warning(f"   Date range in cache: {test_df.index[0]} to {test_df.index[-1]}")
                        logger.warning(f"   Requested range: {self.start_date} to {self.end_date}")
                        logger.warning(f"   ⚠️ Date range mismatch - data exists but not in requested range!")
            else:
                # Normalize timeframe for cache lookup
                cache_timeframe = self.bar_size.lower().replace("minute", "min")
                cached_df = self.cache.load(symbol, cache_timeframe)
            
            if cached_df.empty:
                # STRICT MODE: Fail hard if data is expected but missing (production safety)
                if self.strict_data_mode:
                    error_msg = f"🚨 [CachedDataFeed] STRICT MODE: No cached data found for {symbol} in requested range ({self.start_date} to {self.end_date}). Aborting to prevent trading with incorrect data."
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                
                # Only generate synthetic bars in offline/simulation mode
                # Never use synthetic bars for live trading
                from core.live.scheduler import LiveTradingConfig
                # Check if we're in offline mode (synthetic bars are safe for simulation only)
                # If this is called from live trading, we should not generate synthetic bars
                logger.warning(f"[SyntheticBarFallback] No cached data found for {symbol}")
                
                # Generate synthetic bars ONLY for offline simulation (not live trading)
                # This is safe because offline_mode=True ensures we're not trading with real money
                logger.warning(f"⚠️ [CachedDataFeed] [SyntheticBarFallback] No cached data found for {symbol} - generating SYNTHETIC bars")
                logger.warning(f"   📅 Requested date range: {self.start_date} to {self.end_date}")
                logger.warning(f"   ⚠️ These are SYNTHETIC bars - timestamps will match selected date but prices are simulated")
                
                # Generate synthetic bars with timestamps matching the selected date
                bars_list = self._generate_synthetic_bars(symbol, preload_bars)
                self.cached_data[symbol] = bars_list
                
                if len(bars_list) > 0:
                    first_bar = bars_list[0]
                    last_bar = bars_list[-1]
                    logger.warning(f"⚠️ Generated {len(bars_list)} SYNTHETIC bars for {symbol}")
                    logger.warning(f"   📅 Synthetic bar timestamps: {first_bar.timestamp} to {last_bar.timestamp}")
                    logger.warning(f"   ⚠️ Prices are SIMULATED - not real market data!")
            else:
                # Convert DataFrame to list of Bar objects
                # Filter by start_date and end_date if specified
                import pandas as pd
                bars_list = []
                for idx, row in cached_df.iterrows():
                    bar_time = idx if isinstance(idx, datetime) else pd.to_datetime(idx)
                    if isinstance(bar_time, pd.Timestamp):
                        bar_time = bar_time.to_pydatetime()
                    
                    # Ensure timezone-aware for comparison
                    if bar_time.tzinfo is None:
                        bar_time = bar_time.replace(tzinfo=timezone.utc)
                    
                    # Filter by start_date
                    if self.start_date and bar_time < self.start_date:
                        continue
                    
                    # Filter by end_date
                    if self.end_date and bar_time > self.end_date:
                        continue
                    
                    # Log first bar to verify date filtering is working
                    if len(bars_list) == 0:
                        logger.info(f"📅 [CachedDataFeed] First bar for {symbol}: {bar_time} (start_date filter: {self.start_date})")
                    
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
                if len(bars_list) > 0:
                    first_bar = bars_list[0]
                    last_bar = bars_list[-1]
                    logger.info(f"✅ [CachedDataFeed] Loaded {len(bars_list)} REAL cached bars for {symbol}")
                    logger.info(f"   📅 Date range: {first_bar.timestamp} to {last_bar.timestamp}")
                    logger.info(f"   📅 First bar date: {first_bar.timestamp.strftime('%Y-%m-%d %H:%M:%S %Z') if hasattr(first_bar.timestamp, 'strftime') else first_bar.timestamp}")
                else:
                    logger.warning(f"⚠️ [CachedDataFeed] No bars loaded for {symbol} in date range {self.start_date} to {self.end_date}")
            
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
        
        # Try to get actual price from cache first (for more accurate synthetic bars)
        base_price = None
        try:
            # Get most recent cached price for this symbol (normalize timeframe)
            cache_timeframe = self.bar_size.lower().replace("minute", "min")
            cached_df = self.cache.load(symbol, cache_timeframe)
            if not cached_df.empty:
                base_price = float(cached_df["close"].iloc[-1])
                logger.info(f"📊 [CachedDataFeed] Using cached price {base_price:.2f} as base for synthetic bars")
        except Exception as e:
            logger.debug(f"Could not load cached price for {symbol}: {e}")
        
        # Fallback to default prices if cache lookup failed
        if base_price is None or base_price <= 0:
            default_prices = {
                "QQQ": 600.0,  # Updated to match Nov 2025 prices
                "SPY": 550.0,  # Updated to match Nov 2025 prices
                "SPX": 5500.0,
                "BTC/USD": 50000.0,
                "ETH/USD": 3000.0,
            }
            base_price = default_prices.get(symbol, random.uniform(100.0, 500.0))
            logger.warning(f"⚠️ [CachedDataFeed] Using default price {base_price:.2f} for {symbol} (no cached data found)")
        current_price = base_price
        
        bars_list = []
        
        # Use start_date if available (for historical simulation), otherwise use current time
        if self.start_date:
            # For historical simulation, start from the selected date
            base_time = self.start_date
            logger.info(f"📅 [CachedDataFeed] Generating synthetic bars starting from selected date: {base_time}")
        else:
            # Fallback: use current time (for testing without date selection)
            base_time = datetime.now(timezone.utc)
            logger.warning(f"⚠️ [CachedDataFeed] No start_date specified, using current time for synthetic bars")
        
        # Generate bars going forward in time from start_date
        for i in range(count):
            # Random walk: ±0.5% change per bar
            change_pct = random.uniform(-0.005, 0.005)
            new_price = current_price * (1 + change_pct)
            
            # Generate OHLC
            high = max(current_price, new_price) * (1 + abs(random.uniform(0, 0.002)))
            low = min(current_price, new_price) * (1 - abs(random.uniform(0, 0.002)))
            volume = random.uniform(1000000, 10000000)
            
            # Timestamp: start from base_time and go forward (1 minute per bar for 1Min bars)
            if "Min" in self.bar_size:
                minutes = int(self.bar_size.replace("Min", ""))
                bar_time = base_time + timedelta(minutes=i * minutes)
            else:
                # Default: 1 minute intervals
                bar_time = base_time + timedelta(minutes=i)
            
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
            # CRITICAL FIX: Validate bar symbol matches requested symbol to prevent cross-symbol contamination
            if bar.symbol != symbol:
                logger.error(f"🚨 [CachedDataFeed] SYMBOL MISMATCH: Requested {symbol} but got bar with symbol {bar.symbol}! Discarding bar.")
                # Try to get another bar
                if len(self.bar_buffers[symbol]) > 0:
                    bar = self.bar_buffers[symbol].popleft()
                    if bar.symbol != symbol:
                        logger.error(f"🚨 [CachedDataFeed] Multiple symbol mismatches for {symbol}, returning None")
                        return None
                else:
                    return None
            logger.debug(f"Returning buffered bar for {symbol}: {bar.timestamp}")
            return bar

        # No buffered bars, get next from cached data
        if symbol not in self.cached_data or len(self.cached_data[symbol]) == 0:
            logger.debug(f"No cached data available for {symbol}")
            # SYNTHETIC FALLBACK: Generate synthetic bar if enabled
            if self.synthetic_enabled:
                logger.info(f"🔄 Generating synthetic bar for {symbol} (fallback mode)")
                synthetic_bars = self._generate_synthetic_bars(symbol, count=1)
                if synthetic_bars:
                    self.cached_data[symbol] = synthetic_bars
                    self.current_indices[symbol] = 0
                    bar = synthetic_bars[0]
                    self.current_indices[symbol] = 1
                    logger.info(f"✅ Generated and returned synthetic bar for {symbol}")
                    return bar
            return None

        # Get next bar from cached data
        current_idx = self.current_indices.get(symbol, 0)
        cached_bars = self.cached_data[symbol]
        
        if current_idx >= len(cached_bars):
            logger.debug(f"Reached end of cached data for {symbol}")
            # SYNTHETIC FALLBACK: Generate more synthetic bars if enabled
            if self.synthetic_enabled:
                logger.info(f"🔄 End of cached data for {symbol}, generating more synthetic bars")
                synthetic_bars = self._generate_synthetic_bars(symbol, count=100)
                if synthetic_bars:
                    self.cached_data[symbol].extend(synthetic_bars)
                    bar = synthetic_bars[0]
                    self.current_indices[symbol] = current_idx + 1
                    logger.info(f"✅ Generated and returned additional synthetic bar for {symbol}")
                    return bar
            return None
        
        bar = cached_bars[current_idx]
        # CRITICAL FIX: Validate bar symbol matches requested symbol to prevent cross-symbol contamination
        if bar.symbol != symbol:
            logger.error(f"🚨 [CachedDataFeed] SYMBOL MISMATCH: Requested {symbol} but cached bar at index {current_idx} has symbol {bar.symbol}! This indicates data corruption.")
            # Try to find a bar with the correct symbol
            for idx in range(current_idx, min(current_idx + 10, len(cached_bars))):
                test_bar = cached_bars[idx]
                if test_bar.symbol == symbol:
                    logger.warning(f"⚠️ [CachedDataFeed] Found correct symbol at index {idx}, skipping {idx - current_idx} mismatched bars")
                    self.current_indices[symbol] = idx + 1
                    return test_bar
            logger.error(f"🚨 [CachedDataFeed] No bars with correct symbol {symbol} found in cache, returning None")
            return None
        
        self.current_indices[symbol] = current_idx + 1
        
        logger.debug(f"Returning cached bar {current_idx + 1}/{len(cached_bars)} for {symbol}: {bar.timestamp}, price={bar.close:.2f}")
        return bar

    def get_next_n_bars(self, symbol: str, n: int = 10, timeout: float = 5.0) -> List[Bar]:
        """
        Get next N bars from cached data (batch fetch for better performance).
        
        Args:
            symbol: Symbol to get bars for
            n: Number of bars to fetch
            timeout: Timeout in seconds (not used for cached data)
            
        Returns:
            List of Bar objects (may be less than n if end of data is reached)
        """
        if not self.connected:
            # SYNTHETIC FALLBACK: Generate bars even if not connected (for testing)
            if self.synthetic_enabled:
                logger.info(f"🔄 Not connected but synthetic enabled, generating {n} bars for {symbol}")
                return self._generate_synthetic_bars(symbol, count=n)
            return []

        if symbol not in self.subscribed_symbols:
            # SYNTHETIC FALLBACK: Generate bars even if not subscribed (for testing)
            if self.synthetic_enabled:
                logger.info(f"🔄 Not subscribed but synthetic enabled, generating {n} bars for {symbol}")
                return self._generate_synthetic_bars(symbol, count=n)
            return []

        bars = []
        
        # First, drain buffer if available
        while len(bars) < n and symbol in self.bar_buffers and len(self.bar_buffers[symbol]) > 0:
            bars.append(self.bar_buffers[symbol].popleft())
        
        # If we still need more bars, get from cached data
        if len(bars) < n:
            # CRITICAL: Check if we have cached_data and haven't exhausted it
            # Skip bars that were already processed during preload
            if symbol in self.cached_data and len(self.cached_data[symbol]) > 0:
                current_idx = self.current_indices.get(symbol, 0)
                cached_bars = self.cached_data[symbol]
                
                # Skip past preloaded bars (first 100 bars were already processed)
                # This prevents re-processing the same bars
                if current_idx < 100 and len(cached_bars) > 100:
                    logger.debug(f"⏭️ [CachedDataFeed] Skipping preloaded bars (idx 0-99), starting from idx {current_idx}")
                    # current_idx will be updated by the loop as it processes bars
                
                # Get remaining bars needed
                remaining = n - len(bars)
                available = len(cached_bars) - current_idx
                
                if available > 0:
                    end_idx = min(current_idx + remaining, len(cached_bars))
                    new_bars = cached_bars[current_idx:end_idx]
                    bars.extend(new_bars)
                    self.current_indices[symbol] = end_idx
                    logger.info(f"✅ [CachedDataFeed] Got {len(new_bars)} bars from cached_data for {symbol} (idx {current_idx} to {end_idx}, total cached: {len(cached_bars)})")
                else:
                    logger.warning(f"⚠️ [CachedDataFeed] No more bars available in cached_data for {symbol} (current_idx={current_idx}, total={len(cached_bars)})")
            
            # If still need more bars and cached_data is empty/exhausted, use synthetic fallback
            if len(bars) < n:
                if symbol not in self.cached_data or len(self.cached_data.get(symbol, [])) == 0 or self.current_indices.get(symbol, 0) >= len(self.cached_data.get(symbol, [])):
                    # SYNTHETIC FALLBACK: Generate bars if enabled
                    if self.synthetic_enabled:
                        needed = n - len(bars)
                        logger.info(f"🔄 [CachedDataFeed] No more cached data for {symbol}, generating {needed} synthetic bars")
                        synthetic_bars = self._generate_synthetic_bars(symbol, count=needed)
                        if synthetic_bars:
                            # Add to cached_data for persistence
                            if symbol not in self.cached_data:
                                self.cached_data[symbol] = []
                            self.cached_data[symbol].extend(synthetic_bars)
                            bars.extend(synthetic_bars)
                            logger.info(f"✅ [CachedDataFeed] Generated and added {len(synthetic_bars)} synthetic bars for {symbol}")
                            return bars
                return bars  # Return what we have
        
        return bars

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

