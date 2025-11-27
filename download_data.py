#!/usr/bin/env python3
"""Download historical data using Polygon.io."""

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from polygon import RESTClient
import pandas as pd

load_dotenv()

def download_minute_bars(symbol="QQQ", days=5):
    """Download minute bars for the last N days."""
    api_key = os.getenv("POLYGON_API_KEY")
    client = RESTClient(api_key)

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    print(f"Downloading {symbol} minute bars...")
    print(f"From: {start_date.strftime('%Y-%m-%d')}")
    print(f"To: {end_date.strftime('%Y-%m-%d')}")

    try:
        # Get minute aggregates
        aggs = client.get_aggs(
            symbol,
            1,
            "minute",
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d"),
            limit=50000
        )

        # Convert to DataFrame
        data = []
        for agg in aggs:
            data.append({
                'timestamp': datetime.fromtimestamp(agg.timestamp / 1000),
                'open': agg.open,
                'high': agg.high,
                'low': agg.low,
                'close': agg.close,
                'volume': agg.volume
            })

        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)

        # Save to CSV
        os.makedirs('data', exist_ok=True)
        filename = f'data/{symbol}_1min_{days}days.csv'
        df.to_csv(filename)

        print(f"\n✓ Downloaded {len(df)} bars")
        print(f"✓ Saved to: {filename}")
        print(f"\nData preview:")
        print(df.head())
        print(f"\nDate range: {df.index[0]} to {df.index[-1]}")

        return filename

    except Exception as e:
        print(f"✗ Error: {e}")
        return None

if __name__ == "__main__":
    filename = download_minute_bars("QQQ", days=5)

    if filename:
        print(f"\n{'='*60}")
        print("Next steps:")
        print(f"{'='*60}")
        print(f"\n1. Run a backtest:")
        print(f"   python -m backtesting.cli --data {filename} --symbol QQQ")
        print(f"\n2. View results in the dashboard:")
        print(f"   python main.py --mode api --port 8000")
        print(f"   Open: http://localhost:8000/visualizations/dashboard")
        print(f"\n{'='*60}")
