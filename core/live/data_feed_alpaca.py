"""Alpaca data feed implementation using alpaca-py."""

from __future__ import annotations

import logging
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Deque, List, Optional

from core.live.data_feed import BaseDataFeed
from core.live.types import Bar

logger = logging.getLogger(__name__)


class AlpacaDataFeed(BaseDataFeed):
    """Alpaca data feed using alpaca-py for real-time bars."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = "https://paper-api.alpaca.markets",
        bar_size: str = "1Min",
    ):
        """
        Initialize Alpaca data feed.

        Args:
            api_key: Alpaca API key
            api_secret: Alpaca API secret
            base_url: Alpaca API base URL (default: paper trading)
            bar_size: Bar size (e.g., "1Min", "5Min", "1Hour", "1Day")
        """
        try:
            from alpaca.data.historical import StockHistoricalDataClient
            from alpaca.data.requests import StockBarsRequest
            from alpaca.data.timeframe import TimeFrame
            
            self.api_key = api_key
            self.api_secret = api_secret
            self.base_url = base_url
            self.bar_size = bar_size
            
            # Initialize Alpaca data client
            self.data_client = StockHistoricalDataClient(
                api_key=api_key,
                secret_key=api_secret
            )
            
            # Map bar size to Alpaca TimeFrame
            self.timeframe_map = {
                "1Min": TimeFrame.Minute,
                "5Min": TimeFrame(5, TimeFrame.Minute),
                "15Min": TimeFrame(15, TimeFrame.Minute),
                "1Hour": TimeFrame.Hour,
                "1Day": TimeFrame.Day,
            }
            self.timeframe = self.timeframe_map.get(bar_size, TimeFrame.Minute)
            
            self.subscribed_symbols: List[str] = []
            self.bar_buffers: dict[str, Deque[Bar]] = {}
            self.last_bar_times: dict[str, datetime] = {}
            self.connected = False
            
            logger.info(f"Alpaca data feed initialized (bar_size={bar_size})")
        except ImportError:
            raise ImportError("alpaca-py not installed. Run: pip install alpaca-py")

    def connect(self) -> bool:
        """Connect to Alpaca data feed."""
        self.connected = True
        logger.info("Connected to Alpaca data feed")
        return True

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
            self.last_bar_times[symbol] = datetime.now(timezone.utc) - timedelta(days=1)
            
            # Preload historical bars
            if preload_bars > 0:
                logger.info(f"Preloading {preload_bars} bars for {symbol}...")
                self._preload_historical_bars(symbol, preload_bars)
                loaded = len(self.bar_buffers[symbol])
                logger.info(f"Preload complete for {symbol}: {loaded} bars loaded")

        logger.info(f"Subscribed to symbols: {symbols}")
        return True
    
    def _preload_historical_bars(self, symbol: str, count: int) -> None:
        """Preload historical bars for a symbol."""
        try:
            from alpaca.data.requests import StockBarsRequest
            
            # Calculate start time based on bar size and count needed
            # Request last 2 days of data to ensure we get enough bars (covers weekends/holidays)
            # For 1-minute bars, need ~count minutes of data
            if "Min" in self.bar_size:
                minutes = int(self.bar_size.replace("Min", ""))
                lookback_minutes = count * minutes
                # Use data from 2 days ago to ensure delayed data and avoid subscription errors
                # Request 2 full trading days worth of data (2 days * 390 minutes = 780 minutes)
                now_utc = datetime.now(timezone.utc)
                end_time = now_utc - timedelta(days=2, hours=2)  # 2 days + 2 hours ago (definitely delayed)
                # Request enough to cover 2 full trading days (780 minutes) plus buffer
                start_time = end_time - timedelta(days=2)  # 2 days before end_time
                logger.info(f"Preload requesting {symbol} bars from {start_time} to {end_time} (need {count} bars, requesting ~{int((end_time - start_time).total_seconds() / 60)} minutes)")
            elif "Hour" in self.bar_size:
                hours = int(self.bar_size.replace("Hour", ""))
                lookback_hours = count * hours
                end_time = datetime.now(timezone.utc) - timedelta(days=1)  # 1 day ago
                start_time = end_time - timedelta(hours=lookback_hours + 24)
            else:  # Day
                end_time = datetime.now(timezone.utc) - timedelta(days=1)  # 1 day ago
                start_time = end_time - timedelta(days=count + 7)
            
            # Request historical bars (using delayed data)
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=self.timeframe,
                start=start_time,
                end=end_time,
            )
            
            try:
                logger.info(f"Requesting historical bars for {symbol} from {start_time} to {end_time}")
                bars = self.data_client.get_stock_bars(request)
                logger.info(f"Received BarSet response for {symbol}, type: {type(bars)}")
            except Exception as preload_error:
                logger.error(f"Error getting bars for {symbol}: {preload_error}")
                # If subscription error, try even older data
                if "subscription" in str(preload_error).lower() or "SIP" in str(preload_error):
                    logger.warning(f"Recent data not available for preload, using older data for {symbol}")
                    # Use data from 1 day ago
                    end_time = datetime.now(timezone.utc) - timedelta(days=1)
                    start_time = end_time - timedelta(days=2)
                    request = StockBarsRequest(
                        symbol_or_symbols=symbol,
                        timeframe=self.timeframe,
                        start=start_time,
                        end=end_time,
                    )
                    bars = self.data_client.get_stock_bars(request)
                    logger.info(f"Retry successful, received BarSet for {symbol}")
                else:
                    logger.error(f"Preload failed for {symbol}: {preload_error}")
                    raise
            
            # BarSet can be accessed like a dict with [] operator
            # Don't use 'in' operator - it doesn't work with BarSet
            symbol_bars = None
            try:
                # Direct access: bars[symbol] works even if 'in' doesn't
                symbol_bars = bars[symbol]
                logger.info(f"Successfully accessed bars[{symbol}], got {len(symbol_bars) if hasattr(symbol_bars, '__len__') else 'unknown'} items")
            except (KeyError, TypeError, AttributeError) as e:
                logger.error(f"Error accessing bars[{symbol}]: {e}, BarSet type: {type(bars)}")
                # Try accessing via .data attribute as fallback
                try:
                    if hasattr(bars, 'data') and isinstance(bars.data, dict):
                        symbol_bars = bars.data.get(symbol)
                        logger.info(f"Got bars via .data attribute: {len(symbol_bars) if symbol_bars and hasattr(symbol_bars, '__len__') else 0}")
                except Exception as data_error:
                    logger.error(f"Error accessing bars.data: {data_error}")
                if not symbol_bars:
                    logger.warning(f"No historical bars returned for {symbol}")
                    return
            
            # Convert to list if needed
            if not isinstance(symbol_bars, list):
                try:
                    symbol_bars = list(symbol_bars)
                except:
                    logger.error(f"Could not convert bars to list for {symbol}")
                    return
            
            logger.info(f"Preload received {len(symbol_bars)} bars for {symbol}, requesting last {count}")
            
            # Take last N bars (most recent)
            bars_to_load = symbol_bars[-min(count, len(symbol_bars)):] if symbol_bars else []
            logger.info(f"Loading {len(bars_to_load)} bars into buffer for {symbol}")
            
            # Convert to Bar objects and add to buffer
            loaded_count = 0
            
            for alpaca_bar in bars_to_load:
                try:
                    bar_time = alpaca_bar.timestamp
                    if isinstance(bar_time, datetime):
                        bar_time = bar_time.replace(tzinfo=None)
                    
                    bar = Bar(
                        symbol=symbol,
                        timestamp=bar_time,
                        open=float(alpaca_bar.open),
                        high=float(alpaca_bar.high),
                        low=float(alpaca_bar.low),
                        close=float(alpaca_bar.close),
                        volume=float(alpaca_bar.volume),
                    )
                    
                    self.bar_buffers[symbol].append(bar)
                    loaded_count += 1
                except Exception as bar_error:
                    logger.warning(f"Error converting bar: {bar_error}")
                    continue
            
            # Update last bar time
            if symbol_bars:
                self.last_bar_times[symbol] = symbol_bars[-1].timestamp.replace(tzinfo=None)
            
            logger.info(f"Preloaded {loaded_count} historical bars for {symbol}")
            
        except Exception as e:
            logger.error(f"Error preloading bars for {symbol}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Don't return - let it fail gracefully and continue

    def get_next_bar(self, symbol: str, timeout: float = 5.0) -> Optional[Bar]:
        """Get next bar for symbol. Uses preloaded bars first, then polls for new ones."""
        if not self.connected:
            logger.debug(f"Data feed not connected for {symbol}")
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

        # No preloaded bars available, poll for new bar
        try:
            from alpaca.data.requests import StockBarsRequest
            
            # For live trading, try to get real-time data first, then fall back to delayed
            # Check if we're in live mode (not paper trading)
            is_paper = "paper" in str(self.base_url).lower() if hasattr(self, 'base_url') else True
            
            if is_paper:
                # Alpaca paper trading doesn't have access to recent SIP data
                # Use delayed data (15+ minutes old) to avoid subscription errors
                end_time = datetime.now(timezone.utc) - timedelta(minutes=15)  # Delayed data
                start_time = end_time - timedelta(minutes=10)  # Get last 10 minutes of delayed data
                logger.debug(f"Using delayed data for paper trading: {symbol}")
            else:
                # Live trading - try to get recent data (may need subscription)
                # Try last 5 minutes first
                end_time = datetime.now(timezone.utc)
                start_time = end_time - timedelta(minutes=5)
                logger.debug(f"Attempting real-time data for live trading: {symbol}")
            
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=self.timeframe,
                start=start_time,
                end=end_time,
            )
            
            try:
                bars = self.data_client.get_stock_bars(request)
            except Exception as api_error:
                # If we get subscription error, try even older data
                if "subscription" in str(api_error).lower() or "SIP" in str(api_error):
                    logger.debug(f"Recent data not available, using older delayed data for {symbol}")
                    # Use data from 1 hour ago (definitely delayed)
                    end_time = datetime.now(timezone.utc) - timedelta(hours=1)
                    start_time = end_time - timedelta(minutes=10)
                    request = StockBarsRequest(
                        symbol_or_symbols=symbol,
                        timeframe=self.timeframe,
                        start=start_time,
                        end=end_time,
                    )
                    bars = self.data_client.get_stock_bars(request)
                else:
                    raise
            
            # BarSet doesn't support 'in' operator, access directly
            try:
                symbol_bars = bars[symbol]
                if not symbol_bars:
                    logger.debug(f"No bars returned for {symbol}")
                    return None
            except (KeyError, TypeError, AttributeError):
                logger.debug(f"Symbol {symbol} not found in bars")
                return None

            # Get the most recent bar
            symbol_bars = bars[symbol]
            if not symbol_bars:
                logger.debug(f"No bars in response for {symbol}")
                return None
                
            latest_bar = symbol_bars[-1]
            
            # Check if this is a new bar (not the same as last one)
            bar_time = latest_bar.timestamp
            if isinstance(bar_time, datetime):
                bar_time = bar_time.replace(tzinfo=None)
            
            # Check if we've already seen this bar
            if symbol in self.last_bar_times:
                last_time = self.last_bar_times[symbol]
                if isinstance(last_time, datetime):
                    last_time = last_time.replace(tzinfo=None)
                # Allow bars that are at least 1 minute newer (to handle 1-minute bars)
                time_diff = (bar_time - last_time).total_seconds() if isinstance(bar_time, datetime) and isinstance(last_time, datetime) else 0
                if time_diff < 30:  # Less than 30 seconds difference = same bar
                    logger.debug(f"Bar {bar_time} is not new (last: {last_time}, diff: {time_diff}s)")
                    return None  # Same bar, not new

            self.last_bar_times[symbol] = bar_time
            logger.info(f"New bar received for {symbol}: {bar_time}")

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

    def close(self) -> None:
        """Close data feed."""
        self.connected = False
        self.subscribed_symbols = []
        self.bar_buffers.clear()
        self.last_bar_times.clear()
        logger.info("Alpaca data feed closed")

