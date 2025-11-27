"""Crypto data feed implementation using Alpaca crypto API."""

from __future__ import annotations

import logging
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Deque, List, Optional

from core.live.data_feed import BaseDataFeed
from core.live.types import Bar

logger = logging.getLogger(__name__)


class CryptoDataFeed(BaseDataFeed):
    """Crypto data feed using Alpaca crypto API for BTC and other cryptocurrencies."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = "https://paper-api.alpaca.markets",
        bar_size: str = "1Min",
    ):
        """
        Initialize crypto data feed.

        Args:
            api_key: Alpaca API key
            api_secret: Alpaca API secret
            base_url: Alpaca API base URL (default: paper trading)
            bar_size: Bar size (e.g., "1Min", "5Min", "1Hour", "1Day")
        """
        try:
            from alpaca.data.historical import CryptoHistoricalDataClient
            from alpaca.data.requests import CryptoBarsRequest
            from alpaca.data.timeframe import TimeFrame
            
            self.api_key = api_key
            self.api_secret = api_secret
            self.base_url = base_url
            self.bar_size = bar_size
            
            # Initialize Alpaca crypto data client
            self.data_client = CryptoHistoricalDataClient(
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
            
            logger.info(f"Crypto data feed initialized (bar_size={bar_size})")
        except ImportError:
            raise ImportError("alpaca-py not installed. Run: pip install alpaca-py")

    def connect(self) -> bool:
        """Connect to crypto data feed."""
        self.connected = True
        logger.info("Connected to Alpaca crypto data feed")
        return True

    def subscribe(self, symbols: List[str], preload_bars: int = 60) -> bool:
        """
        Subscribe to crypto symbols and preload historical bars.
        
        Args:
            symbols: List of crypto symbols (e.g., ["BTC/USD", "ETH/USD"])
            preload_bars: Number of historical bars to preload
        """
        if not self.connected:
            logger.error("Cannot subscribe: not connected")
            return False

        self.subscribed_symbols = symbols
        for symbol in symbols:
            self.bar_buffers[symbol] = deque(maxlen=500)
            self.last_bar_times[symbol] = datetime.now(timezone.utc)
            
            # Preload historical bars
            if preload_bars > 0:
                logger.info(f"Preloading {preload_bars} bars for {symbol}...")
                self._preload_historical_bars(symbol, preload_bars)
                loaded = len(self.bar_buffers[symbol])
                logger.info(f"Preload complete for {symbol}: {loaded} bars loaded")

        logger.info(f"Subscribed to crypto symbols: {symbols}")
        return True

    def _preload_historical_bars(self, symbol: str, count: int) -> None:
        """Preload historical bars for a crypto symbol."""
        try:
            from alpaca.data.requests import CryptoBarsRequest
            
            # Calculate time window (request more than needed to ensure we get enough)
            end_time = datetime.now(timezone.utc)
            # For 1-minute bars, request 2 days to ensure enough data
            start_time = end_time - timedelta(days=2)
            
            request = CryptoBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=self.timeframe,
                start=start_time,
                end=end_time,
            )
            
            try:
                bars = self.data_client.get_crypto_bars(request)
            except Exception as e:
                # If subscription error, try older data
                if "subscription" in str(e).lower() or "SIP" in str(e).lower():
                    logger.debug(f"Recent data not available for {symbol}, using delayed data")
                    end_time = datetime.now(timezone.utc) - timedelta(hours=1)
                    start_time = end_time - timedelta(days=2)
                    request = CryptoBarsRequest(
                        symbol_or_symbols=symbol,
                        timeframe=self.timeframe,
                        start=start_time,
                        end=end_time,
                    )
                    bars = self.data_client.get_crypto_bars(request)
                else:
                    raise
            
            # Extract bars for symbol
            try:
                symbol_bars = bars[symbol]
            except (KeyError, TypeError, AttributeError):
                logger.warning(f"No bars returned for {symbol}")
                return
            
            if not symbol_bars:
                return
            
            # Convert to list if needed
            if not isinstance(symbol_bars, list):
                symbol_bars = list(symbol_bars)
            
            # Take last N bars (most recent)
            bars_to_load = symbol_bars[-min(count, len(symbol_bars)):]
            
            logger.info(f"Loading {len(bars_to_load)} bars into buffer for {symbol}")
            
            for alpaca_bar in bars_to_load:
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
            
            if self.bar_buffers[symbol]:
                self.last_bar_times[symbol] = self.bar_buffers[symbol][-1].timestamp
            
            logger.info(f"Preloaded {len(self.bar_buffers[symbol])} historical bars for {symbol}")

        except Exception as e:
            logger.error(f"Error preloading bars for {symbol}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

    def get_next_bar(self, symbol: str, timeout: float = 5.0) -> Optional[Bar]:
        """Get next bar for crypto symbol."""
        if not self.connected:
            logger.debug(f"Data feed not connected for {symbol}")
            return None

        if symbol not in self.subscribed_symbols:
            logger.debug(f"Symbol {symbol} not subscribed")
            return None

        # Check if we have bars in buffer
        if symbol in self.bar_buffers and len(self.bar_buffers[symbol]) > 0:
            bar = self.bar_buffers[symbol].popleft()
            self.last_bar_times[symbol] = bar.timestamp
            logger.debug(f"Returning preloaded bar for {symbol}: {bar.timestamp}")
            return bar
        
        # If buffer is empty, try to fetch new bars
        logger.debug(f"Buffer empty for {symbol}, fetching new bars...")
        try:
            from alpaca.data.requests import CryptoBarsRequest
            
            # Request last hour of data
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=1)
            
            request = CryptoBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=self.timeframe,
                start=start_time,
                end=end_time,
            )
            
            try:
                bars = self.data_client.get_crypto_bars(request)
            except Exception as e:
                # If subscription error, try older data
                if "subscription" in str(e).lower():
                    logger.debug(f"Recent data not available for {symbol}, using delayed data")
                    end_time = datetime.now(timezone.utc) - timedelta(hours=1)
                    start_time = end_time - timedelta(hours=2)
                    request = CryptoBarsRequest(
                        symbol_or_symbols=symbol,
                        timeframe=self.timeframe,
                        start=start_time,
                        end=end_time,
                    )
                    bars = self.data_client.get_crypto_bars(request)
                else:
                    raise
            
            # Extract bars for symbol
            try:
                symbol_bars = bars[symbol]
            except (KeyError, TypeError, AttributeError):
                logger.warning(f"No bars returned for {symbol}")
                return None
            
            if not symbol_bars:
                return None
            
            # Convert to list if needed
            if not isinstance(symbol_bars, list):
                symbol_bars = list(symbol_bars)
            
            # Add new bars to buffer (skip if already have them)
            for alpaca_bar in symbol_bars:
                bar_time = alpaca_bar.timestamp
                if isinstance(bar_time, datetime):
                    bar_time = bar_time.replace(tzinfo=None)
                
                # Skip if we already have this bar
                if self.bar_buffers[symbol] and self.bar_buffers[symbol][-1].timestamp >= bar_time:
                    continue
                
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
            
            # Return first bar from buffer
            if len(self.bar_buffers[symbol]) > 0:
                bar = self.bar_buffers[symbol].popleft()
                self.last_bar_times[symbol] = bar.timestamp
                logger.debug(f"Returning newly fetched bar for {symbol}: {bar.timestamp}")
                return bar
            
        except Exception as e:
            logger.error(f"Error fetching bars for {symbol}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        
        return None

    def close(self) -> None:
        """Close crypto data feed."""
        self.connected = False
        self.subscribed_symbols = []
        self.bar_buffers.clear()
        self.last_bar_times.clear()
        logger.info("Crypto data feed closed")

