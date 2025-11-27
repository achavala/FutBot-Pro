"""Background data collection service for offline trading support."""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

from core.config import load_config
from services.cache import BarCache

logger = logging.getLogger(__name__)


class DataCollector:
    """Background service that continuously collects and stores market data."""

    def __init__(
        self,
        symbols: List[str],
        bar_size: str = "1Min",
        cache_path: Optional[Path] = None,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
    ):
        """
        Initialize data collector.

        Args:
            symbols: List of symbols to collect data for
            bar_size: Bar size (e.g., "1Min", "5Min")
            cache_path: Path to cache database
            api_key: Alpaca API key (optional, uses env if not provided)
            api_secret: Alpaca API secret (optional, uses env if not provided)
        """
        self.symbols = symbols
        self.bar_size = bar_size
        self.cache_path = cache_path or Path("data/cache.db")
        self.cache = BarCache(self.cache_path)
        
        # Load API keys from environment if not provided
        import os
        from dotenv import load_dotenv
        load_dotenv()
        
        self.api_key = api_key or os.getenv("ALPACA_API_KEY")
        self.api_secret = api_secret or os.getenv("ALPACA_SECRET_KEY")
        
        if not self.api_key or not self.api_secret:
            raise ValueError("Alpaca API keys required for data collection")
        
        # Initialize Alpaca client
        try:
            from alpaca.data.historical import StockHistoricalDataClient
            from alpaca.data.timeframe import TimeFrame
            
            self.data_client = StockHistoricalDataClient(
                api_key=self.api_key,
                secret_key=self.api_secret
            )
            
            # Map bar size to TimeFrame
            self.timeframe_map = {
                "1Min": TimeFrame.Minute,
                "5Min": TimeFrame(5, TimeFrame.Minute),
                "15Min": TimeFrame(15, TimeFrame.Minute),
                "1Hour": TimeFrame.Hour,
                "1Day": TimeFrame.Day,
            }
            self.timeframe = self.timeframe_map.get(bar_size, TimeFrame.Minute)
            
        except ImportError:
            raise ImportError("alpaca-py not installed. Run: pip install alpaca-py")
        
        self.is_running = False
        self.collector_thread: Optional[threading.Thread] = None
        self.last_collection_times: dict[str, datetime] = {}
        
        logger.info(f"Data collector initialized for symbols: {symbols}, bar_size: {bar_size}")

    def _is_trading_hours(self) -> bool:
        """Check if current time is within US market trading hours (9:30 AM - 4:00 PM ET)."""
        now_et = datetime.now(timezone.utc).astimezone()
        # Convert to ET (simplified - doesn't handle DST)
        # ET is UTC-5 (EST) or UTC-4 (EDT)
        et_offset = -5 if now_et.month < 3 or now_et.month > 11 else -4
        et_time = datetime.now(timezone.utc) + timedelta(hours=et_offset)
        
        # Check if weekday (Monday=0, Sunday=6)
        if et_time.weekday() >= 5:  # Saturday or Sunday
            return False
        
        # Check time (9:30 AM - 4:00 PM ET)
        hour = et_time.hour
        minute = et_time.minute
        if hour < 9 or (hour == 9 and minute < 30):
            return False
        if hour >= 16:
            return False
        
        return True

    def _collect_bars(self, symbol: str) -> int:
        """Collect latest bars for a symbol and store in cache."""
        try:
            from alpaca.data.requests import StockBarsRequest
            
            # Determine time range
            # Collect last 1 hour of data (or more if we haven't collected recently)
            end_time = datetime.now(timezone.utc)
            
            # If we've collected before, start from last collection time
            # Otherwise, collect last 24 hours
            if symbol in self.last_collection_times:
                start_time = self.last_collection_times[symbol] - timedelta(minutes=5)  # 5 min overlap
            else:
                start_time = end_time - timedelta(hours=24)
            
            # Request bars
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=self.timeframe,
                start=start_time,
                end=end_time,
            )
            
            try:
                bars = self.data_client.get_stock_bars(request)
            except Exception as e:
                # If subscription error or no data, try older data
                if "subscription" in str(e).lower() or "SIP" in str(e).lower():
                    logger.debug(f"Recent data not available for {symbol}, using delayed data")
                    end_time = datetime.now(timezone.utc) - timedelta(hours=1)
                    start_time = end_time - timedelta(hours=2)
                    request = StockBarsRequest(
                        symbol_or_symbols=symbol,
                        timeframe=self.timeframe,
                        start=start_time,
                        end=end_time,
                    )
                    bars = self.data_client.get_stock_bars(request)
                else:
                    raise
            
            # Extract bars for symbol
            try:
                symbol_bars = bars[symbol]
            except (KeyError, TypeError, AttributeError):
                logger.warning(f"No bars returned for {symbol}")
                return 0
            
            if not symbol_bars:
                return 0
            
            # Convert to list if needed
            if not isinstance(symbol_bars, list):
                symbol_bars = list(symbol_bars)
            
            # Convert to DataFrame format for cache
            import pandas as pd
            
            bars_data = []
            for alpaca_bar in symbol_bars:
                bar_time = alpaca_bar.timestamp
                if isinstance(bar_time, datetime):
                    bar_time = bar_time.replace(tzinfo=None)
                
                bars_data.append({
                    "timestamp": int(bar_time.timestamp() * 1000),  # milliseconds
                    "open": float(alpaca_bar.open),
                    "high": float(alpaca_bar.high),
                    "low": float(alpaca_bar.low),
                    "close": float(alpaca_bar.close),
                    "volume": float(alpaca_bar.volume),
                    "vwap": float(getattr(alpaca_bar, 'vwap', alpaca_bar.close)),
                    "trades": int(getattr(alpaca_bar, 'trade_count', 0)),
                })
            
            if not bars_data:
                return 0
            
            # Create DataFrame
            df = pd.DataFrame(bars_data)
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            
            # Store in cache
            self.cache.store(symbol, self.bar_size, df)
            
            # Update last collection time
            if symbol_bars:
                last_bar_time = symbol_bars[-1].timestamp
                if isinstance(last_bar_time, datetime):
                    self.last_collection_times[symbol] = last_bar_time.replace(tzinfo=None)
                else:
                    self.last_collection_times[symbol] = datetime.now(timezone.utc)
            
            logger.info(f"Collected {len(bars_data)} bars for {symbol}")
            return len(bars_data)
            
        except Exception as e:
            logger.error(f"Error collecting bars for {symbol}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return 0

    def _collection_loop(self) -> None:
        """Main collection loop running in background thread."""
        logger.info("Data collector started")
        
        while self.is_running:
            try:
                # Collect data for each symbol
                for symbol in self.symbols:
                    if not self.is_running:
                        break
                    
                    try:
                        self._collect_bars(symbol)
                    except Exception as e:
                        logger.error(f"Error collecting data for {symbol}: {e}")
                
                # Sleep between collections
                # During trading hours: collect every 1 minute
                # Outside trading hours: collect every 5 minutes (for after-hours/pre-market)
                if self._is_trading_hours():
                    sleep_seconds = 60  # 1 minute during trading hours
                else:
                    sleep_seconds = 300  # 5 minutes outside trading hours
                
                time.sleep(sleep_seconds)
                
            except Exception as e:
                logger.error(f"Error in collection loop: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
        
        logger.info("Data collector stopped")

    def start(self) -> None:
        """Start the data collector in background thread."""
        if self.is_running:
            logger.warning("Data collector already running")
            return
        
        self.is_running = True
        self.collector_thread = threading.Thread(target=self._collection_loop, daemon=True)
        self.collector_thread.start()
        logger.info("Data collector started in background")

    def stop(self) -> None:
        """Stop the data collector."""
        if not self.is_running:
            return
        
        self.is_running = False
        if self.collector_thread:
            self.collector_thread.join(timeout=5.0)
        logger.info("Data collector stopped")

    def get_status(self) -> dict:
        """Get collector status."""
        return {
            "is_running": self.is_running,
            "symbols": self.symbols,
            "bar_size": self.bar_size,
            "last_collection_times": {
                symbol: time.isoformat() if isinstance(time, datetime) else None
                for symbol, time in self.last_collection_times.items()
            },
            "is_trading_hours": self._is_trading_hours(),
        }

