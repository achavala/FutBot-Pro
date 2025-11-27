#!/usr/bin/env python3
"""
Start data collector service to gather market data for offline testing.
This should run continuously to collect data before market closes.
"""

import sys
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.live.data_feed_alpaca import AlpacaDataFeed
from core.cache.bar_cache import BarCache

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataCollector:
    """Collects market data and stores in cache for offline use."""
    
    def __init__(self, symbols=None, interval_seconds=60):
        self.symbols = symbols or ["SPY", "QQQ"]
        self.interval_seconds = interval_seconds
        self.data_feed = None
        self.cache = BarCache()
        self.running = False
        
        # Initialize data feed
        try:
            self.data_feed = AlpacaDataFeed(symbols=self.symbols)
            logger.info(f"Data collector initialized for symbols: {self.symbols}")
        except Exception as e:
            logger.error(f"Failed to initialize data feed: {e}")
            raise
    
    def start(self, duration_hours=24):
        """Start collecting data for specified duration."""
        self.running = True
        end_time = datetime.now() + timedelta(hours=duration_hours)
        
        logger.info(f"Starting data collection for {duration_hours} hours")
        logger.info(f"Will collect until: {end_time}")
        
        try:
            while self.running and datetime.now() < end_time:
                for symbol in self.symbols:
                    try:
                        # Get latest bar
                        bar = self.data_feed.get_next_bar(symbol, timeout=5.0)
                        
                        if bar:
                            # Store in cache
                            self.cache.store_bar(
                                symbol=symbol,
                                timeframe="1min",
                                bar=bar
                            )
                            logger.info(f"Collected bar for {symbol}: {bar.timestamp}, close={bar.close}")
                        else:
                            logger.debug(f"No new bar for {symbol}")
                            
                    except Exception as e:
                        logger.warning(f"Error collecting data for {symbol}: {e}")
                
                # Sleep until next interval
                time.sleep(self.interval_seconds)
                
        except KeyboardInterrupt:
            logger.info("Data collection interrupted by user")
        finally:
            self.running = False
            logger.info("Data collection stopped")
    
    def stop(self):
        """Stop data collection."""
        self.running = False


def main():
    """Run data collector."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Collect market data for offline testing")
    parser.add_argument("--symbols", nargs="+", default=["SPY", "QQQ"], help="Symbols to collect")
    parser.add_argument("--duration", type=int, default=24, help="Duration in hours")
    parser.add_argument("--interval", type=int, default=60, help="Collection interval in seconds")
    
    args = parser.parse_args()
    
    try:
        collector = DataCollector(symbols=args.symbols, interval_seconds=args.interval)
        collector.start(duration_hours=args.duration)
    except Exception as e:
        logger.error(f"Data collector failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
