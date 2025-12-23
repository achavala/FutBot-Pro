#!/usr/bin/env python3
"""Test script to verify Massive API connection and real-time data collection."""

import argparse
import logging
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.config.polygon import PolygonSettings
from services.cache import BarCache
from services.polygon_client import PolygonClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def test_massive_api_connection(symbol: str = "QQQ", duration: int = 60):
    """Test Massive API connection and real-time data collection."""
    logger.info("=" * 80)
    logger.info("🧪 Massive API Connection & Real-Time Data Test")
    logger.info("=" * 80)
    logger.info(f"Symbol: {symbol}")
    logger.info(f"Duration: {duration} seconds")
    logger.info("")
    
    # Load Massive API settings
    try:
        logger.info("🔵 Loading Massive API settings...")
        settings = PolygonSettings.load()
        logger.info(f"✅ API Key loaded: {settings.api_key[:10]}...{settings.api_key[-4:]}")
        logger.info(f"✅ Base URL: {settings.rest_url}")
    except Exception as e:
        logger.error(f"❌ Failed to load Massive API settings: {e}")
        logger.error("   Make sure MASSIVE_API_KEY or POLYGON_API_KEY is set in:")
        logger.error("   - config/settings.yaml (polygon.api_key)")
        logger.error("   - Environment variable (MASSIVE_API_KEY or POLYGON_API_KEY)")
        sys.exit(1)
    
    # Initialize Polygon client
    cache_path = Path("data/cache.db")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        logger.info("🔵 Initializing Polygon client...")
        client = PolygonClient(settings, cache_path)
        logger.info("✅ Polygon client initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Polygon client: {e}")
        sys.exit(1)
    
    # Test historical data fetch
    logger.info("")
    logger.info("🔵 Testing historical data fetch...")
    try:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=1)
        
        logger.info(f"   Fetching bars from {start_time} to {end_time}...")
        bars_df = client.get_historical_bars(
            symbol=symbol,
            timeframe="1Min",
            start=start_time,
            end=end_time,
        )
        
        if bars_df.empty:
            logger.warning("⚠️  No bars returned (market may be closed)")
        else:
            logger.info(f"✅ Received {len(bars_df)} bars")
            latest_bar = bars_df.index[-1]
            if isinstance(latest_bar, pd.Timestamp):
                latest_bar = latest_bar.to_pydatetime()
            
            time_diff = (datetime.now(timezone.utc) - latest_bar.replace(tzinfo=timezone.utc)).total_seconds()
            logger.info(f"   Latest bar: {latest_bar}")
            logger.info(f"   Time difference: {time_diff:.1f} seconds")
            
            if time_diff < 300:  # Less than 5 minutes
                logger.info("✅ Data is recent (real-time capable)")
            elif time_diff < 3600:  # Less than 1 hour
                logger.warning("⚠️  Data is delayed (within 1 hour)")
            else:
                logger.warning("⚠️  Data is stale (older than 1 hour)")
    except Exception as e:
        logger.error(f"❌ Historical data fetch failed: {type(e).__name__}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
    
    # Test real-time data collection loop
    logger.info("")
    logger.info("🔵 Testing real-time data collection loop...")
    logger.info(f"   Collecting data for {duration} seconds...")
    logger.info("   (Press Ctrl+C to stop early)")
    logger.info("")
    
    cache = BarCache(cache_path)
    start_time = time.time()
    collection_count = 0
    
    try:
        while time.time() - start_time < duration:
            try:
                # Collect latest bars
                end_time = datetime.now(timezone.utc)
                start_collect = end_time - timedelta(minutes=5)  # Last 5 minutes
                
                bars_df = client.get_historical_bars(
                    symbol=symbol,
                    timeframe="1Min",
                    start=start_collect,
                    end=end_time,
                )
                
                if not bars_df.empty:
                    collection_count += 1
                    latest_bar = bars_df.index[-1]
                    if isinstance(latest_bar, pd.Timestamp):
                        latest_bar = latest_bar.to_pydatetime()
                    
                    time_diff = (datetime.now(timezone.utc) - latest_bar.replace(tzinfo=timezone.utc)).total_seconds()
                    logger.info(
                        f"⏱️  [{int(time.time() - start_time)}s] "
                        f"Collected {len(bars_df)} bars | "
                        f"Latest: {latest_bar.strftime('%H:%M:%S')} | "
                        f"Age: {time_diff:.0f}s"
                    )
                else:
                    logger.warning(f"⏱️  [{int(time.time() - start_time)}s] No new bars")
                
                # Wait 30 seconds between collections
                time.sleep(30)
                
            except KeyboardInterrupt:
                logger.info("\n⚠️  Interrupted by user")
                break
            except Exception as e:
                logger.error(f"Error during collection: {e}")
                time.sleep(10)  # Wait before retrying
        
    except Exception as e:
        logger.error(f"❌ Collection loop failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    # Summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("📊 TEST SUMMARY")
    logger.info("=" * 80)
    logger.info(f"✅ API Connection: Working")
    logger.info(f"✅ Historical Data: Working")
    logger.info(f"✅ Real-Time Collection: {'Working' if collection_count > 0 else 'No data collected'}")
    logger.info(f"   Collections made: {collection_count}")
    logger.info("")
    logger.info("💡 Next Steps:")
    logger.info("   1. Start DataCollector service: curl -X POST http://localhost:8000/data-collector/start")
    logger.info("   2. Monitor data collection: curl http://localhost:8000/data-collector/status")
    logger.info("   3. Start live trading: The bot will automatically use cached data from Massive API")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Massive API Connection")
    parser.add_argument("--symbol", type=str, default="QQQ", help="Symbol to test")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds")
    args = parser.parse_args()
    
    test_massive_api_connection(symbol=args.symbol, duration=args.duration)

