# 🔍 Live Trading Diagnosis

## Current Status

**Live trading IS running, but data feed appears stuck:**

- ✅ Status: `is_running: true`
- ✅ Mode: `live`
- ⚠️ **Bars per symbol: Only 2 bars (SPY: 2, QQQ: 2)**
- ⚠️ **Last bar time: 2025-11-28T20:02:00 (OLD DATA!)**
- ⚠️ **This is why the UI shows "loading" - waiting for new bars**

## Problem

The Alpaca data feed is not fetching new bars. Possible causes:

1. **Market is closed** - If it's after hours or weekend, Alpaca won't return new bars
2. **Data feed connection issue** - Alpaca API might be rate-limited or disconnected
3. **Stuck in replay mode** - If it's using cached data, it might be stuck on old dates

## Solution

### Option 1: Stop and Restart Live Trading

```bash
# Stop current session
curl -X POST http://localhost:8000/live/stop

# Wait 2 seconds, then restart
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["SPY", "QQQ"],
    "broker_type": "alpaca",
    "offline_mode": false,
    "testing_mode": true,
    "fixed_investment_amount": 10000.0
  }'
```

### Option 2: Check Market Hours

If market is closed (after 4 PM ET or weekend), live trading won't get new bars. In this case:

1. **Wait for market open** (9:30 AM ET on weekdays)
2. **Or use simulation mode** for testing with historical data

### Option 3: Check Alpaca Connection

```bash
# Test Alpaca API directly
python3 << 'EOF'
import os
from dotenv import load_dotenv
load_dotenv()

from alpaca.trading.client import TradingClient

api_key = os.getenv("ALPACA_API_KEY")
api_secret = os.getenv("ALPACA_SECRET_KEY")

try:
    client = TradingClient(api_key, api_secret, paper=True)
    account = client.get_account()
    print(f"✅ Alpaca connected: {account.account_number}")
    print(f"   Status: {account.status}")
    print(f"   Buying Power: ${float(account.buying_power):,.2f}")
except Exception as e:
    print(f"❌ Alpaca connection failed: {e}")
EOF
```

## Quick Fix from Dashboard

1. **Click "Stop" button** in the dashboard
2. **Wait 2-3 seconds**
3. **Click "Start Live" button** again
4. **Watch the bar count** - should start increasing if market is open

## Expected Behavior

- **During market hours (9:30 AM - 4:00 PM ET):**
  - Bar count should increase every minute
  - Last bar time should be recent (within last 1-2 minutes)
  - Trading starts automatically at 30+ bars

- **After market hours:**
  - Bar count stays frozen
  - Last bar time is from market close
  - This is normal - no new data until next market open

## Next Steps

1. **Check current time** - Is market open?
2. **Stop and restart** if market is open but bars aren't updating
3. **Use simulation mode** if you want to test with historical data

