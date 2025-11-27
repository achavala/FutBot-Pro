#!/usr/bin/env python3
"""Test Alpaca preload to see how many bars we actually get."""

import os
import sys
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

try:
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    
    api_key = os.getenv("ALPACA_API_KEY")
    api_secret = os.getenv("ALPACA_SECRET_KEY")
    
    if not api_key or not api_secret:
        print("ERROR: ALPACA_API_KEY and ALPACA_SECRET_KEY must be set")
        sys.exit(1)
    
    client = StockHistoricalDataClient(api_key=api_key, secret_key=api_secret)
    
    # Request last 2 days of data
    now_utc = datetime.now(timezone.utc)
    end_time = now_utc - timedelta(days=2, hours=2)
    start_time = end_time - timedelta(days=2)
    
    print(f"Requesting QQQ bars from {start_time} to {end_time}")
    
    request = StockBarsRequest(
        symbol_or_symbols="QQQ",
        timeframe=TimeFrame.Minute,
        start=start_time,
        end=end_time,
    )
    
    bars = client.get_stock_bars(request)
    
    # BarSet can be accessed like a dict with []
    qqq_bars = bars["QQQ"] if "QQQ" in bars else None
    if qqq_bars:
        print(f"\n✅ Received {len(qqq_bars)} bars for QQQ")
        if len(qqq_bars) > 0:
            print(f"First bar: {qqq_bars[0].timestamp}")
            print(f"Last bar: {qqq_bars[-1].timestamp}")
            print(f"\nFirst 5 bars:")
            for i, bar in enumerate(qqq_bars[:5]):
                print(f"  {i+1}. {bar.timestamp} - O:{bar.open:.2f} H:{bar.high:.2f} L:{bar.low:.2f} C:{bar.close:.2f}")
            print(f"\nLast 5 bars:")
            for i, bar in enumerate(qqq_bars[-5:]):
                print(f"  {len(qqq_bars)-4+i}. {bar.timestamp} - O:{bar.open:.2f} H:{bar.high:.2f} L:{bar.low:.2f} C:{bar.close:.2f}")
    else:
        print("❌ No QQQ bars in response")
        print(f"BarSet type: {type(bars)}")
        print(f"BarSet data: {bars}")
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

