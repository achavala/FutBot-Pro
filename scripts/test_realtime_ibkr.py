#!/usr/bin/env python3
"""
Test script to verify IBKR real-time bar subscriptions are working.

This script:
1. Connects to IBKR TWS/Gateway
2. Subscribes to real-time bars for a symbol
3. Monitors incoming bars and displays timestamps
4. Verifies bars are current (not historical)
"""

import sys
import time
import logging
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ib_insync import IB, Stock, util
from core.live.types import Bar

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_realtime_subscription(symbol: str = "QQQ", host: str = "127.0.0.1", port: int = 7497, duration: int = 60):
    """
    Test real-time bar subscription for a symbol.
    
    Args:
        symbol: Symbol to subscribe to (default: QQQ)
        host: IBKR host (default: 127.0.0.1)
        port: IBKR port (default: 7497 for paper trading)
        duration: How long to monitor (seconds, default: 60)
    """
    ib = IB()
    bars_received = []
    subscription_active = False
    
    try:
        logger.info(f"🔵 Connecting to IBKR at {host}:{port}...")
        ib.connect(host, port, clientId=999)  # Use high client ID to avoid conflicts
        
        if not ib.isConnected():
            logger.error("❌ Failed to connect to IBKR")
            return False
        
        logger.info("✅ Connected to IBKR")
        
        # Create contract
        contract = Stock(symbol, "SMART", "USD")
        logger.info(f"📊 Contract: {contract}")
        
        # Test 1: Request historical data first (to verify connection works)
        logger.info("🔵 Testing historical data request...")
        try:
            historical_bars = ib.reqHistoricalData(
                contract,
                endDateTime="",
                durationStr="1 H",  # Must have space: "1 H" not "1H"
                barSizeSetting="1 min",
                whatToShow="TRADES",
                useRTH=False,
                formatDate=1,
            )
            ib.sleep(2)
            
            if historical_bars:
                latest_historical = historical_bars[-1]
                hist_time = latest_historical.date.replace(tzinfo=None) if hasattr(latest_historical.date, 'replace') else latest_historical.date
                logger.info(f"✅ Historical data works - Latest bar: {hist_time} @ ${latest_historical.close:.2f}")
            else:
                logger.warning("⚠️ No historical bars returned")
        except Exception as e:
            logger.error(f"❌ Historical data request failed: {e}")
            return False
        
        # Test 2: Subscribe to real-time bars
        logger.info("🔵 Subscribing to real-time bars...")
        logger.info(f"   Symbol: {symbol}")
        logger.info(f"   Bar size: 60 seconds (1 minute)")
        logger.info(f"   Duration: {duration} seconds")
        
        try:
            # Subscribe to 1-minute real-time bars
            realtime_bar_list = ib.reqRealTimeBars(
                contract,
                barSize=60,  # 60 seconds = 1 minute
                whatToShow="TRADES",
                useRTH=False,  # Allow after-hours data
            )
            
            # Wait a moment for subscription to establish
            ib.sleep(1)
            
            if realtime_bar_list is None:
                logger.error("❌ Real-time subscription returned None")
                return False
            
            subscription_active = True
            logger.info("✅ Real-time subscription established")
            
            # Set up callback to track bars
            def on_bar_update(realtime_bar_list, has_new_bar: bool):
                if has_new_bar and realtime_bar_list:
                    try:
                        # Get the latest bar
                        latest_bar = realtime_bar_list[-1] if isinstance(realtime_bar_list, list) else realtime_bar_list
                        
                        # Extract timestamp
                        bar_time = latest_bar.time.replace(tzinfo=None) if hasattr(latest_bar.time, 'replace') else latest_bar.time
                        if isinstance(bar_time, datetime):
                            bar_time = bar_time.replace(tzinfo=None)
                        
                        # Calculate time difference from now
                        now = datetime.now(timezone.utc).replace(tzinfo=None)
                        if bar_time.tzinfo:
                            bar_time = bar_time.replace(tzinfo=None)
                        
                        time_diff = (now - bar_time).total_seconds()
                        
                        # Store bar info
                        bar_info = {
                            'timestamp': bar_time,
                            'close': float(latest_bar.close),
                            'volume': float(latest_bar.volume),
                            'time_diff_seconds': time_diff,
                            'is_realtime': time_diff < 120  # Consider real-time if within 2 minutes
                        }
                        bars_received.append(bar_info)
                        
                        # Display bar info
                        status = "🟢 REAL-TIME" if bar_info['is_realtime'] else "🟡 DELAYED"
                        logger.info(
                            f"{status} Bar received: {bar_time.strftime('%Y-%m-%d %H:%M:%S')} "
                            f"@ ${bar_info['close']:.2f} | "
                            f"Vol: {bar_info['volume']:.0f} | "
                            f"Age: {time_diff:.1f}s"
                        )
                        
                    except Exception as e:
                        logger.error(f"❌ Error processing real-time bar: {e}")
                        import traceback
                        logger.debug(traceback.format_exc())
            
            # Attach callback
            realtime_bar_list.updateEvent += on_bar_update
            logger.info("✅ Callback attached to real-time subscription")
            
            # Monitor for specified duration
            logger.info(f"⏱️  Monitoring real-time bars for {duration} seconds...")
            logger.info("   (Press Ctrl+C to stop early)")
            logger.info("")
            
            start_time = time.time()
            last_bar_count = 0
            
            while time.time() - start_time < duration:
                ib.sleep(1)
                
                # Show progress every 10 seconds
                elapsed = int(time.time() - start_time)
                if elapsed % 10 == 0 and elapsed > 0:
                    new_bars = len(bars_received) - last_bar_count
                    logger.info(f"⏱️  {elapsed}s elapsed | Bars received: {len(bars_received)} (+{new_bars} in last 10s)")
                    last_bar_count = len(bars_received)
            
            # Summary
            logger.info("")
            logger.info("=" * 80)
            logger.info("📊 TEST SUMMARY")
            logger.info("=" * 80)
            logger.info(f"Total bars received: {len(bars_received)}")
            
            if bars_received:
                realtime_count = sum(1 for b in bars_received if b['is_realtime'])
                delayed_count = len(bars_received) - realtime_count
                
                logger.info(f"  🟢 Real-time bars: {realtime_count} ({realtime_count/len(bars_received)*100:.1f}%)")
                logger.info(f"  🟡 Delayed bars: {delayed_count} ({delayed_count/len(bars_received)*100:.1f}%)")
                
                if bars_received:
                    latest = bars_received[-1]
                    logger.info(f"  Latest bar: {latest['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
                    logger.info(f"  Latest price: ${latest['close']:.2f}")
                    logger.info(f"  Age: {latest['time_diff_seconds']:.1f} seconds")
                
                # Check if we got any real-time bars
                if realtime_count > 0:
                    logger.info("")
                    logger.info("✅ SUCCESS: Real-time subscription is working!")
                    logger.info("   Real-time bars are being received.")
                else:
                    logger.info("")
                    logger.warning("⚠️  WARNING: No real-time bars received")
                    logger.warning("   All bars are delayed. Possible reasons:")
                    logger.warning("   1. Market data subscription not enabled in TWS")
                    logger.warning("   2. Paper trading account may only have delayed data")
                    logger.warning("   3. Market is closed")
            else:
                logger.warning("⚠️  No bars received during test period")
                logger.warning("   Possible reasons:")
                logger.warning("   1. Market is closed")
                logger.warning("   2. Real-time subscription failed")
                logger.warning("   3. No market data permissions")
            
            # Cancel subscription
            logger.info("")
            logger.info("🔵 Cancelling real-time subscription...")
            ib.cancelRealTimeBars(realtime_bar_list)
            logger.info("✅ Subscription cancelled")
            
        except Exception as e:
            logger.error(f"❌ Real-time subscription failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
        
        return True
        
    except KeyboardInterrupt:
        logger.info("")
        logger.info("⏹️  Test interrupted by user")
        if subscription_active:
            try:
                ib.cancelRealTimeBars(realtime_bar_list)
            except:
                pass
        return False
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
        
    finally:
        if ib.isConnected():
            logger.info("🔵 Disconnecting from IBKR...")
            ib.disconnect()
            logger.info("✅ Disconnected")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test IBKR real-time bar subscriptions")
    parser.add_argument("--symbol", default="QQQ", help="Symbol to test (default: QQQ)")
    parser.add_argument("--host", default="127.0.0.1", help="IBKR host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=7497, help="IBKR port (default: 7497 for paper)")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds (default: 60)")
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("🧪 IBKR Real-Time Bar Subscription Test")
    print("=" * 80)
    print(f"Symbol: {args.symbol}")
    print(f"Host: {args.host}:{args.port}")
    print(f"Duration: {args.duration} seconds")
    print("")
    print("⚠️  Make sure TWS/IB Gateway is running and connected!")
    print("")
    
    # Ensure ib_insync event loop is started
    try:
        util.startLoop()
    except RuntimeError:
        pass  # Loop already running
    
    success = test_realtime_subscription(
        symbol=args.symbol,
        host=args.host,
        port=args.port,
        duration=args.duration
    )
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

