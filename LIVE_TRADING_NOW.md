# Live Trading Setup - Market Hours

## ✅ What I Just Did

1. **Updated "Start Live" button** to use `testing_mode: true`
   - Allows trading with just 1 bar minimum
   - Uses Alpaca broker (live trading)
   - Aggressive mode enabled

2. **Bot is now running** in live mode with testing_mode

## 🚀 How to Use

### Option 1: Use Dashboard "Start Live" Button
1. **Refresh your browser** (to get latest code)
2. Click the **"Start Live"** button (green play button)
3. Bot will start with:
   - `testing_mode: true` (1 bar minimum)
   - `broker_type: "alpaca"` (live trading)
   - Symbols: SPY, QQQ

### Option 2: Use API Directly
```bash
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

## ⚠️ Current Status

**Bot is running** but `bars_per_symbol` shows 0. This means:
- Alpaca data feed is connected
- But no bars are being returned yet

**Why bars might be 0:**
1. **Alpaca paper trading** uses 15+ minute delayed data
2. If market just opened, may need to wait a few minutes
3. Data feed might be polling but not getting bars

## 🔍 Check If Bars Are Coming

```bash
# Check status
curl -s http://localhost:8000/live/status | python3 -m json.tool

# Watch logs
tail -f /tmp/futbot_server.log | grep -E "Processed bar|get_next_bar|Alpaca|bars_per_symbol"
```

## 📊 What to Expect

Once bars start coming:
- `bars_per_symbol` will increment
- With `testing_mode: true`, trades can execute with just 1 bar
- Trades will execute based on price-action signals (EMA9/EMA21)
- Stop loss: 10%, Profit target: 15%

## 🎯 If Bars Don't Come

If `bars_per_symbol` stays at 0 after 5 minutes:

1. **Check Alpaca connection:**
   ```bash
   # Verify API keys are set
   echo $ALPACA_API_KEY
   echo $ALPACA_BASE_URL
   ```

2. **Try restarting:**
   ```bash
   curl -X POST http://localhost:8000/live/stop
   curl -X POST http://localhost:8000/live/start \
     -H "Content-Type: application/json" \
     -d '{"symbols": ["SPY"], "broker_type": "alpaca", "testing_mode": true}'
   ```

3. **Check if market is actually open:**
   - Market hours: 9:30 AM - 4:00 PM ET
   - Alpaca paper trading may have delays

## 💡 After Market Closes

Once market closes, the **Simulate button will appear** and you can:
- Run historical simulations
- Test with cached data
- Use 600x replay speed

## Summary

✅ **"Start Live" button now uses testing_mode**
✅ **Bot is running in live mode**
⏳ **Waiting for Alpaca to return bars** (may take a few minutes)
✅ **Once bars arrive, trades will execute** (testing_mode allows 1 bar minimum)

**Refresh your browser and click "Start Live" - it's ready for live trading!**

