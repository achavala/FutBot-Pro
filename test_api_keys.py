#!/usr/bin/env python3
"""Quick test of API keys."""

import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("Testing API Keys")
print("=" * 60)

# Test Polygon
print("\n1. Testing Polygon.io...")
try:
    from polygon import RESTClient
    api_key = os.getenv("POLYGON_API_KEY")
    client = RESTClient(api_key)

    # Try a simple aggregates query (works with free tier)
    aggs = client.get_aggs("AAPL", 1, "day", "2024-01-01", "2024-01-02")
    print(f"✓ Polygon.io: WORKING")
    print(f"  Sample data: AAPL had {len(aggs)} bars")
except Exception as e:
    print(f"✗ Polygon.io: {str(e)[:80]}")

# Test Finnhub
print("\n2. Testing Finnhub...")
try:
    import finnhub
    api_key = os.getenv("FINNHUB_API_KEY")
    client = finnhub.Client(api_key=api_key)

    # Get a simple quote
    quote = client.quote("AAPL")
    print(f"✓ Finnhub: WORKING")
    print(f"  AAPL current price: ${quote['c']}")
except Exception as e:
    print(f"✗ Finnhub: {str(e)[:80]}")

# Test Alpha Vantage
print("\n3. Testing Alpha Vantage...")
try:
    import requests
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=AAPL&apikey={api_key}"
    response = requests.get(url)
    data = response.json()

    if "Global Quote" in data:
        print(f"✓ Alpha Vantage: WORKING")
        price = data["Global Quote"].get("05. price", "N/A")
        print(f"  AAPL price: ${price}")
    else:
        print(f"✗ Alpha Vantage: {data.get('Note', data.get('Error Message', 'Unknown error'))}")
except Exception as e:
    print(f"✗ Alpha Vantage: {str(e)[:80]}")

# Check Alpaca
print("\n4. Checking Alpaca...")
alpaca_key = os.getenv("ALPACA_API_KEY")
if alpaca_key and not alpaca_key.startswith("your_"):
    try:
        from alpaca.trading.client import TradingClient
        secret_key = os.getenv("ALPACA_SECRET_KEY")
        client = TradingClient(alpaca_key, secret_key, paper=True)
        account = client.get_account()
        print(f"✓ Alpaca: WORKING")
        print(f"  Account: {account.account_number}")
        print(f"  Cash: ${float(account.cash):,.2f}")
    except Exception as e:
        print(f"✗ Alpaca: {str(e)[:80]}")
else:
    print("⚠ Alpaca: Not configured (keys still have placeholders)")
    print("  → Sign up at https://alpaca.markets/ to get paper trading keys")

print("\n" + "=" * 60)
print("Summary")
print("=" * 60)
print("\nFor demo mode (no API keys needed):")
print("  python main.py --mode api --port 8000 --demo")
print("\nFor paper trading (requires working API keys):")
print("  python main.py --mode live --symbol QQQ --capital 100000")
print("=" * 60)
