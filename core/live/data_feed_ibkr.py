"""Interactive Brokers data feed implementation using ib_insync."""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Deque, List, Optional

from ib_insync import IB, Stock, util

from core.live.data_feed import BaseDataFeed
from core.live.types import Bar

logger = logging.getLogger(__name__)

# Thread pool for running IB operations to avoid event loop conflicts
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ibkr_data")
_loop_started = False
_loop_lock = threading.Lock()


def _ensure_loop():
    """Ensure ib_insync event loop is running in a separate thread (lazy initialization)."""
    global _loop_started
    with _loop_lock:
        if not _loop_started:
            def start_loop():
                try:
                    # Check if we're using uvloop (can't patch it)
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        if 'uvloop' in str(type(loop)):
                            logger.warning("Skipping IBKR loop start (uvloop detected)")
                            return
                    except RuntimeError:
                        pass
                    
                    util.startLoop()
                except RuntimeError:
                    pass  # Loop already running
                except Exception as e:
                    # If loop patching fails (e.g., with uvloop), continue without it
                    logger.warning(f"Could not start IBKR loop: {e}")
                    return
            
            # Start loop in executor thread
            _executor.submit(start_loop)
            time.sleep(0.1)  # Give loop time to start
            _loop_started = True


class IBKRDataFeed(BaseDataFeed):
    """IBKR data feed using ib_insync for real-time bars."""

    def __init__(
        self,
        broker_client=None,
        ib_instance: Optional[IB] = None,
        bar_size: str = "1 min",
        what_to_show: str = "TRADES",
        polygon_client=None,
        cache_path: Optional[Path] = None,
    ):
        """
        Initialize IBKR data feed.

        Args:
            broker_client: IBKRBrokerClient instance (preferred - shares connection)
            ib_instance: Existing IB instance (alternative to broker_client)
            bar_size: Bar size (e.g., "1 min", "5 mins")
            what_to_show: What to show (TRADES, MIDPOINT, BID, ASK)
            polygon_client: Optional PolygonClient for cache fallback
            cache_path: Optional path to cache database
        """
        self.broker_client = broker_client
        self.ib = ib_instance
        self.bar_size = bar_size
        self.what_to_show = what_to_show
        self.polygon_client = polygon_client
        self.cache_path = cache_path
        self.subscribed_symbols: List[str] = []
        self.bar_buffers: dict[str, Deque[Bar]] = {}
        self.last_bar_times: dict[str, datetime] = {}
        self.connected = False
        self._connection_lock = threading.Lock()
        self._use_existing_ib = ib_instance is not None or broker_client is not None

    def connect(self) -> bool:
        """Connect to IBKR (or use existing connection)."""
        with self._connection_lock:
            if self.connected:
                return True

            # Get IB instance from broker_client if available
            if self.broker_client and hasattr(self.broker_client, 'ib'):
                self.ib = self.broker_client.ib
                if self.ib and self.ib.isConnected():
                    self.connected = True
                    logger.info("Using IBKR connection from broker client")
                    return True

            # Or use provided IB instance
            if self.ib and self.ib.isConnected():
                self.connected = True
                logger.info("Using existing IBKR connection for data feed")
                return True

            # If broker_client provided but not connected, try to connect it
            if self.broker_client and hasattr(self.broker_client, 'connect'):
                if self.broker_client.connect():
                    self.ib = self.broker_client.ib
                    self.connected = True
                    logger.info("Connected IBKR broker client for data feed")
                    return True

            logger.error("Cannot connect: no IB instance or broker client available")
            self.connected = False
            return False

    def subscribe(self, symbols: List[str], preload_bars: int = 60) -> bool:
        """
        Subscribe to symbols and preload historical bars.
        
        Args:
            symbols: List of symbols to subscribe to
            preload_bars: Number of historical bars to preload (default 60)
        """
        if not self.connected:
            logger.error("Cannot subscribe: not connected")
            return False

        self.subscribed_symbols = symbols
        for symbol in symbols:
            self.bar_buffers[symbol] = deque(maxlen=500)
            self.last_bar_times[symbol] = datetime.now() - timedelta(days=1)
            
            # Preload historical bars (synchronously - wait for completion)
            if preload_bars > 0:
                logger.info(f"Preloading {preload_bars} bars for {symbol}...")
                self._preload_historical_bars(symbol, preload_bars)
                loaded = len(self.bar_buffers[symbol])
                logger.info(f"Preload complete for {symbol}: {loaded} bars loaded")

        logger.info(f"Subscribed to symbols: {symbols}")
        return True
    
    def _preload_historical_bars(self, symbol: str, count: int) -> None:
        """Preload historical bars for a symbol. Tries Polygon cache first, then IBKR."""
        # First, try to load from Polygon cache if available
        cache_loaded = self._try_load_from_cache(symbol, count)
        if cache_loaded >= count:
            logger.info(f"Preloaded {cache_loaded} bars for {symbol} from cache (target: {count})")
            return
        
        # If cache didn't have enough, try IBKR
        if not self.ib or not self.ib.isConnected():
            logger.warning(f"Cannot preload bars for {symbol}: not connected to IBKR")
            if cache_loaded > 0:
                logger.info(f"Using {cache_loaded} bars from cache (partial preload)")
            return
        
        try:
            def _load_bars():
                try:
                    contract = Stock(symbol, "SMART", "USD")
                    
                    # Use shorter duration for faster response
                    # "1 H" = 1 hour (60 minutes) should be enough for 50+ bars
                    # This is much faster than "1 D" (1 day)
                    duration_str = "1 H"  # Must have space: "1 H" not "1H"
                    
                    logger.info(f"Requesting historical data from IBKR for {symbol} (duration: {duration_str})...")
                    
                    # Request with longer timeout and allow after-hours data
                    bars = self.ib.reqHistoricalData(
                        contract,
                        endDateTime="",
                        durationStr=duration_str,
                        barSizeSetting=self.bar_size,
                        whatToShow=self.what_to_show,
                        useRTH=False,  # Allow after-hours data
                        formatDate=1,
                    )
                    # Wait for data to arrive (ib_insync needs time)
                    self.ib.sleep(2)
                    
                    if not bars:
                        logger.warning(f"No historical bars returned from IBKR for {symbol}")
                        return 0
                    
                    logger.info(f"Received {len(bars)} bars from IBKR for {symbol}")
                    
                    # Convert to Bar objects and add to buffer
                    loaded_count = 0
                    # Take last N bars, but use all if we got fewer
                    bars_to_load = bars[-min(count, len(bars)):] if bars else []
                    for ib_bar in bars_to_load:
                        try:
                            bar_time = ib_bar.date.replace(tzinfo=None) if hasattr(ib_bar.date, 'replace') else ib_bar.date
                            if isinstance(bar_time, datetime):
                                bar_time = bar_time.replace(tzinfo=None)
                            
                            # Skip if we already have this bar from cache
                            if symbol in self.bar_buffers:
                                if any(b.timestamp == bar_time for b in self.bar_buffers[symbol]):
                                    continue
                            
                            bar = Bar(
                                symbol=symbol,
                                timestamp=bar_time,
                                open=float(ib_bar.open),
                                high=float(ib_bar.high),
                                low=float(ib_bar.low),
                                close=float(ib_bar.close),
                                volume=float(ib_bar.volume),
                            )
                            
                            self.bar_buffers[symbol].append(bar)
                            loaded_count += 1
                        except Exception as bar_error:
                            logger.warning(f"Error converting bar: {bar_error}")
                            continue
                    
                    # Update last bar time
                    if bars:
                        self.last_bar_times[symbol] = bars[-1].date.replace(tzinfo=None)
                    
                    logger.info(f"Preloaded {loaded_count} new bars from IBKR for {symbol} (total: {len(self.bar_buffers[symbol])})")
                    return loaded_count
                    
                except Exception as e:
                    logger.error(f"Error preloading bars from IBKR for {symbol}: {e}")
                    import traceback
                    logger.debug(traceback.format_exc())
                    return 0
            
            # Run in thread to avoid event loop conflicts
            # Increased timeout to 90s, but handle partial loads gracefully
            future = _executor.submit(_load_bars)
            try:
                ibkr_loaded = future.result(timeout=90)  # 90 second timeout for historical data
                total_loaded = len(self.bar_buffers.get(symbol, []))
                if total_loaded < count:
                    logger.warning(f"Partial preload for {symbol}: {total_loaded}/{count} bars loaded. Bot will accumulate bars naturally.")
                else:
                    logger.info(f"Preload complete for {symbol}: {total_loaded} bars loaded")
            except Exception as timeout_error:
                total_loaded = len(self.bar_buffers.get(symbol, []))
                logger.warning(f"Preload timeout for {symbol} after 90s. Loaded {total_loaded}/{count} bars. Bot will continue with available bars.")
                # Continue anyway - some bars may have loaded
            
        except Exception as e:
            logger.error(f"Failed to preload bars for {symbol}: {e}")
            total_loaded = len(self.bar_buffers.get(symbol, []))
            if total_loaded > 0:
                logger.info(f"Using {total_loaded} bars from cache/partial preload")
    
    def _try_load_from_cache(self, symbol: str, count: int) -> int:
        """Try to load bars from Polygon cache. Returns number of bars loaded."""
        if not self.polygon_client and not self.cache_path:
            return 0
        
        try:
            # Try using Polygon client if available
            if self.polygon_client:
                # Convert bar_size to Polygon timeframe format
                timeframe = self._ibkr_to_polygon_timeframe(self.bar_size)
                if timeframe:
                    bars_df = self.polygon_client.get_latest_bars(symbol, timeframe, count)
                    if not bars_df.empty and len(bars_df) > 0:
                        loaded = 0
                        for _, row in bars_df.tail(count).iterrows():
                            try:
                                bar_time = row.name if hasattr(row.name, 'replace') else datetime.fromtimestamp(row.name.timestamp())
                                if isinstance(bar_time, datetime):
                                    bar_time = bar_time.replace(tzinfo=None)
                                
                                bar = Bar(
                                    symbol=symbol,
                                    timestamp=bar_time,
                                    open=float(row['open']),
                                    high=float(row['high']),
                                    low=float(row['low']),
                                    close=float(row['close']),
                                    volume=float(row.get('volume', 0)),
                                )
                                
                                if symbol not in self.bar_buffers:
                                    self.bar_buffers[symbol] = deque(maxlen=500)
                                
                                # Avoid duplicates
                                if not any(b.timestamp == bar.timestamp for b in self.bar_buffers[symbol]):
                                    self.bar_buffers[symbol].append(bar)
                                    loaded += 1
                            except Exception as e:
                                logger.debug(f"Error loading bar from cache: {e}")
                                continue
                        
                        if loaded > 0:
                            logger.info(f"Loaded {loaded} bars for {symbol} from Polygon cache")
                            return loaded
            
            # Try direct cache access if cache_path provided
            if self.cache_path:
                from services.cache import BarCache
                cache = BarCache(self.cache_path)
                timeframe = self._ibkr_to_polygon_timeframe(self.bar_size)
                if timeframe:
                    bars_df = cache.load(symbol, timeframe)
                    if not bars_df.empty and len(bars_df) > 0:
                        loaded = 0
                        for _, row in bars_df.tail(count).iterrows():
                            try:
                                bar_time = row.name if hasattr(row.name, 'replace') else datetime.fromtimestamp(row.name.timestamp())
                                if isinstance(bar_time, datetime):
                                    bar_time = bar_time.replace(tzinfo=None)
                                
                                bar = Bar(
                                    symbol=symbol,
                                    timestamp=bar_time,
                                    open=float(row['open']),
                                    high=float(row['high']),
                                    low=float(row['low']),
                                    close=float(row['close']),
                                    volume=float(row.get('volume', 0)),
                                )
                                
                                if symbol not in self.bar_buffers:
                                    self.bar_buffers[symbol] = deque(maxlen=500)
                                
                                if not any(b.timestamp == bar.timestamp for b in self.bar_buffers[symbol]):
                                    self.bar_buffers[symbol].append(bar)
                                    loaded += 1
                            except Exception as e:
                                logger.debug(f"Error loading bar from cache: {e}")
                                continue
                        
                        if loaded > 0:
                            logger.info(f"Loaded {loaded} bars for {symbol} from cache")
                            return loaded
        
        except Exception as e:
            logger.debug(f"Cache load failed for {symbol}: {e}")
        
        return 0
    
    def _ibkr_to_polygon_timeframe(self, ibkr_bar_size: str) -> Optional[str]:
        """Convert IBKR bar size to Polygon timeframe format."""
        # IBKR: "1 min", "5 mins", "1 hour", "1 day"
        # Polygon: "1Min", "5Min", "1Hour", "1Day"
        try:
            parts = ibkr_bar_size.strip().split()
            if len(parts) < 2:
                return None
            
            number = parts[0]
            unit = parts[1].lower()
            
            if unit.startswith('min'):
                return f"{number}Min"
            elif unit.startswith('hour'):
                return f"{number}Hour"
            elif unit.startswith('day'):
                return f"{number}Day"
        except:
            pass
        return None

    def get_next_bar(self, symbol: str, timeout: float = 5.0) -> Optional[Bar]:
        """Get next bar for symbol. Uses preloaded bars first, then requests new ones."""
        # Ensure we have IB instance
        if self.broker_client and hasattr(self.broker_client, 'ib'):
            self.ib = self.broker_client.ib

        if not self.connected:
            logger.debug(f"Data feed not connected for {symbol}")
            return None
            
        if not self.ib:
            logger.debug(f"No IB instance available for {symbol}")
            return None

        if symbol not in self.subscribed_symbols:
            logger.debug(f"Symbol {symbol} not subscribed")
            return None

        # First, check if we have preloaded bars we haven't used yet
        if symbol in self.bar_buffers and len(self.bar_buffers[symbol]) > 0:
            # Get the oldest bar from buffer (FIFO)
            bar = self.bar_buffers[symbol].popleft()
            logger.debug(f"Returning preloaded bar for {symbol}: {bar.timestamp}")
            return bar

        # No preloaded bars available, request new one (but with longer timeout)
        try:
            # Request latest bar using historical data
            def _get_bar():
                try:
                    if not self.ib:
                        logger.warning(f"No IB instance in thread for {symbol}")
                        return None
                        
                    if not self.ib.isConnected():
                        logger.warning(f"IB not connected for {symbol}")
                        return None

                    # Create contract
                    contract = Stock(symbol, "SMART", "USD")

                    # Request the most recent bar (duration 2 minutes, endDateTime empty = now)
                    try:
                        bars = self.ib.reqHistoricalData(
                            contract,
                            endDateTime="",
                            durationStr="1 D",  # Get last day, then take most recent bar
                            barSizeSetting=self.bar_size,
                            whatToShow=self.what_to_show,
                            useRTH=False,  # Allow after-hours data
                            formatDate=1,
                        )
                        # Wait for data
                        self.ib.sleep(1)
                    except Exception as req_error:
                        logger.error(f"reqHistoricalData failed for {symbol}: {type(req_error).__name__}: {req_error}")
                        return None

                    if not bars:
                        logger.debug(f"No bars returned for {symbol}")
                        return None

                    # Get the most recent complete bar
                    latest_bar = bars[-1]

                    # Check if this is a new bar (not the same as last one)
                    bar_time = latest_bar.date.replace(tzinfo=None) if hasattr(latest_bar.date, 'replace') else latest_bar.date
                    if isinstance(bar_time, datetime):
                        bar_time = bar_time.replace(tzinfo=None)
                    
                    if symbol in self.last_bar_times:
                        if bar_time <= self.last_bar_times[symbol]:
                            return None  # Same bar, not new

                    self.last_bar_times[symbol] = bar_time

                    # Convert to our Bar type
                    bar = Bar(
                        symbol=symbol,
                        timestamp=bar_time,
                        open=float(latest_bar.open),
                        high=float(latest_bar.high),
                        low=float(latest_bar.low),
                        close=float(latest_bar.close),
                        volume=float(latest_bar.volume),
                    )

                    # Store in buffer
                    self.bar_buffers[symbol].append(bar)

                    return bar

                except Exception as e:
                    logger.error(f"Error getting bar for {symbol}: {type(e).__name__}: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    return None

            # Run in thread to avoid event loop conflicts
            # Use longer timeout for historical data requests (30 seconds)
            future = _executor.submit(_get_bar)
            result = future.result(timeout=30.0)  # Longer timeout for API calls
            return result

        except Exception as e:
            logger.error(f"Error in get_next_bar for {symbol}: {type(e).__name__}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def close(self) -> None:
        """Close data feed."""
        self.connected = False
        self.subscribed_symbols = []
        self.bar_buffers.clear()
        self.last_bar_times.clear()
        # Don't disconnect IB instance if it was provided via broker_client
        if not self.broker_client and not self._use_existing_ib and self.ib:
            try:
                self.ib.disconnect()
            except:
                pass
        logger.info("IBKR data feed closed")

