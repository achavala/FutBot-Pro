#!/usr/bin/env python3
"""
Live Data Watchdog - Monitors when live trading data starts flowing
Pings every 5 seconds and confirms when first live bar is received
"""

import time
import requests
import json
from datetime import datetime
from typing import Optional

API_BASE = "http://localhost:8000"


def get_live_status() -> Optional[dict]:
    """Get current live trading status."""
    try:
        response = requests.get(f"{API_BASE}/live/status", timeout=2)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"❌ Error fetching status: {e}")
    return None


def format_timestamp(ts: str) -> str:
    """Format ISO timestamp to readable format."""
    try:
        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S %Z')
    except:
        return ts


def main():
    print("=" * 70)
    print("📡 LIVE DATA WATCHDOG - Monitoring for First Live Bar")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Monitoring every 5 seconds...")
    print("Press Ctrl+C to stop")
    print("=" * 70)
    print()

    last_bar_time = None
    first_live_bar_received = False
    check_count = 0

    try:
        while True:
            check_count += 1
            status = get_live_status()

            if not status:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️  Cannot connect to API")
                time.sleep(5)
                continue

            is_running = status.get('is_running', False)
            current_bar_time = status.get('last_bar_time')
            bars_per_symbol = status.get('bars_per_symbol', {})
            mode = status.get('mode', 'unknown')
            bar_count = status.get('bar_count', 0)

            # Check if we got a new bar
            if current_bar_time and current_bar_time != last_bar_time:
                bar_date = datetime.fromisoformat(current_bar_time.replace('Z', '+00:00'))
                now = datetime.now(bar_date.tzinfo)
                age_minutes = (now - bar_date).total_seconds() / 60

                # Check if this is a "live" bar (from today, less than 1 hour old)
                is_today = bar_date.date() == now.date()
                is_recent = age_minutes < 60

                if is_today and is_recent and not first_live_bar_received:
                    first_live_bar_received = True
                    print()
                    print("=" * 70)
                    print("🟢 LIVE FEED ACTIVE!")
                    print("=" * 70)
                    print(f"📡 First live bar received: {format_timestamp(current_bar_time)}")
                    print(f"📊 Bars per symbol: {bars_per_symbol}")
                    print(f"🔢 Total bars: {bar_count}")
                    print(f"⏰ Age: {age_minutes:.1f} minutes")
                    print()
                    print("✅ Trading strategies will now activate")
                    print("✅ GEX calculations will begin")
                    print("✅ Options agents will evaluate")
                    print("✅ Real Alpaca paper orders will execute")
                    print("=" * 70)
                    print()
                elif not first_live_bar_received:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📅 Bar from {format_timestamp(current_bar_time)} (age: {age_minutes:.1f} min) - waiting for today's data...")

                last_bar_time = current_bar_time

            # Status update every 30 checks (2.5 minutes)
            if check_count % 30 == 0:
                if is_running:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏳ Still waiting... (Running: {is_running}, Mode: {mode}, Bars: {bar_count})")
                else:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️  Live trading not running")

            time.sleep(5)

    except KeyboardInterrupt:
        print()
        print("=" * 70)
        print("🛑 Watchdog stopped by user")
        if first_live_bar_received:
            print("✅ Live data was successfully detected!")
        else:
            print("⚠️  Live data not yet received (market may be closed)")
        print("=" * 70)


if __name__ == "__main__":
    main()

