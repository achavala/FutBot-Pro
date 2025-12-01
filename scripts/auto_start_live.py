#!/usr/bin/env python3
"""
Auto-start live trading when market data becomes available.

This script polls the API to detect when live market bars start flowing,
then automatically starts the live trading session.
"""

import time
import json
import urllib.request
import urllib.error
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

API_BASE = "http://localhost:8000"
POLL_INTERVAL = 30  # Check every 30 seconds
TIMEOUT = 5  # Request timeout in seconds


def _fetch_json(url: str, timeout: int = TIMEOUT) -> dict:
    """Fetch JSON from URL using urllib (built-in, no dependencies)."""
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        logger.debug(f"Error fetching {url}: {e}")
        return {}


def check_market_status() -> dict:
    """Check if market is open."""
    return _fetch_json(f"{API_BASE}/market/status") or {"is_open": False}


def check_live_status() -> dict:
    """Check current live trading status."""
    return _fetch_json(f"{API_BASE}/live/status") or {"is_running": False, "mode": "backtest"}


def has_live_bars() -> bool:
    """Check if live bars are being received."""
    try:
        status = check_live_status()
        last_bar_time = status.get("last_bar_time")
        
        if not last_bar_time:
            return False
        
        # Parse timestamp (handle ISO format)
        try:
            # Try ISO format first
            if 'T' in last_bar_time:
                bar_time = datetime.fromisoformat(last_bar_time.replace('Z', '+00:00'))
            else:
                # Fallback to simple format
                bar_time = datetime.strptime(last_bar_time, "%Y-%m-%d %H:%M:%S")
            
            now = datetime.now(bar_time.tzinfo) if bar_time.tzinfo else datetime.now()
            
            # Check if bar is from today and recent (within last hour)
            if bar_time.date() == now.date():
                time_diff = (now - bar_time).total_seconds()
                if time_diff < 3600:  # Within last hour
                    logger.info(f"✅ Live bars detected: {bar_time} (age: {time_diff/60:.1f} min)")
                    return True
        except Exception as e:
            logger.debug(f"Error parsing bar time: {e}")
        
        return False
    except Exception as e:
        logger.debug(f"Error checking for live bars: {e}")
        return False


def start_live_trading() -> bool:
    """Start live trading session."""
    logger.info("🚀 Attempting to start live trading...")
    
    try:
        payload = {
            "symbols": ["SPY", "QQQ"],
            "broker_type": "alpaca",
            "offline_mode": False,
            "testing_mode": True,
            "fixed_investment_amount": 10000.0
        }
        
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            f"{API_BASE}/live/start",
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                logger.info("✅ Live trading started successfully!")
                return True
            else:
                body = response.read().decode('utf-8')
                logger.error(f"❌ Failed to start live trading: {response.status} - {body}")
                return False
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8') if hasattr(e, 'read') else str(e)
        logger.error(f"❌ HTTP error starting live trading: {e.code} - {body}")
        return False
    except Exception as e:
        logger.error(f"❌ Error starting live trading: {e}")
        return False


def main():
    """Main loop - wait for market data and auto-start."""
    logger.info("=" * 60)
    logger.info("AUTO-START LIVE TRADING - Waiting for Market Data")
    logger.info("=" * 60)
    logger.info(f"API Base: {API_BASE}")
    logger.info(f"Poll Interval: {POLL_INTERVAL} seconds")
    logger.info("")
    
    # Check initial status
    market_status = check_market_status()
    live_status = check_live_status()
    
    logger.info(f"Market Status: {'OPEN' if market_status.get('is_open') else 'CLOSED'}")
    logger.info(f"Live Trading: {'RUNNING' if live_status.get('is_running') else 'STOPPED'}")
    logger.info(f"Mode: {live_status.get('mode', 'unknown')}")
    logger.info("")
    
    # If already running, exit
    if live_status.get("is_running"):
        logger.info("✅ Live trading is already running. Exiting.")
        return
    
    logger.info("Waiting for live market bars to start flowing...")
    logger.info("(Alpaca Paper provides 15-min delayed data after market opens)")
    logger.info("")
    
    consecutive_checks = 0
    required_checks = 2  # Require 2 consecutive checks to confirm data is flowing
    
    while True:
        try:
            # Check if live bars are available
            if has_live_bars():
                consecutive_checks += 1
                logger.info(f"✅ Live bars detected ({consecutive_checks}/{required_checks})")
                
                if consecutive_checks >= required_checks:
                    logger.info("")
                    logger.info("🎯 Live data confirmed - Starting trading session!")
                    logger.info("")
                    
                    if start_live_trading():
                        logger.info("")
                        logger.info("=" * 60)
                        logger.info("✅ AUTO-START COMPLETE")
                        logger.info("=" * 60)
                        logger.info("Live trading is now active.")
                        logger.info("Monitor the dashboard for trade activity.")
                        logger.info("")
                        break
                    else:
                        logger.warning("Failed to start - will retry on next check")
                        consecutive_checks = 0  # Reset on failure
            else:
                consecutive_checks = 0  # Reset if no bars
                current_time = datetime.now().strftime("%H:%M:%S")
                logger.info(f"[{current_time}] No live bars yet - waiting...")
            
            # Sleep before next check
            time.sleep(POLL_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("")
            logger.info("Interrupted by user. Exiting.")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()

