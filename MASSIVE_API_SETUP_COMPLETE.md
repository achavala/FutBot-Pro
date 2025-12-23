# Massive API Real-Time Data Setup - COMPLETE ✅

## Summary

The system has been successfully configured to use **Massive API (Polygon)** for real-time data collection, bypassing the IBKR market data subscription requirement.

---

## ✅ What Was Completed

### 1. **DataCollector Enhanced** ✅
- Updated `services/data_collector.py` to support both Massive API and Alpaca API
- Prioritizes Massive API when available (better for real-time data)
- Automatically falls back to Alpaca if Massive API is not configured
- Supports real-time data collection during market hours

### 2. **IBKRDataFeed Enhanced** ✅
- Updated `core/live/data_feed_ibkr.py` to check Massive API cache for recent data
- Priority order:
  1. Real-time bars from IBKR subscription (if available)
  2. Preloaded bars from buffer
  3. **Recent bars from Massive API cache (NEW)**
  4. Historical polling from IBKR (fallback)

### 3. **Test Script Created** ✅
- Created `scripts/test_massive_api.py` to verify Massive API connection
- Tests historical data fetch
- Tests real-time data collection loop
- Provides diagnostic information

---

## 🔧 Configuration

### API Key Setup

The Massive API key is already configured in `config/settings.yaml`:

```yaml
polygon:
  api_key: jYAUGrzcdiRWvR8ibZDkybyWKS9uG2ep
  rest_url: https://api.massive.com
  rate_limit_per_min: 5
```

**Alternative:** You can also set it via environment variable:
```bash
export MASSIVE_API_KEY=your_api_key
# OR
export POLYGON_API_KEY=your_api_key
```

---

## 🧪 Testing

### Test Massive API Connection

```bash
# Basic test (30 seconds)
python scripts/test_massive_api.py --symbol QQQ --duration 30

# Custom symbol and duration
python scripts/test_massive_api.py --symbol SPY --duration 60
```

**Expected Output:**
```
✅ API Connection: Working
✅ Historical Data: Working
✅ Real-Time Collection: Working (during market hours)
```

---

## 🚀 Usage

### 1. Start DataCollector Service

The DataCollector will automatically use Massive API if available:

```bash
# Start data collector
curl -X POST http://localhost:8000/data-collector/start \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["QQQ"], "bar_size": "1Min"}'

# Check status
curl http://localhost:8000/data-collector/status
```

**Response:**
```json
{
  "is_running": true,
  "symbols": ["QQQ"],
  "bar_size": "1Min",
  "api_type": "Massive API",
  "last_collection_times": {
    "QQQ": "2025-12-20T15:30:00"
  },
  "is_trading_hours": true
}
```

### 2. Start Live Trading

When you start live trading with IBKR, the system will:

1. **Try IBKR real-time subscription** (may fail with Error 420 if no market data permissions)
2. **Check Massive API cache** for recent bars (within last 5 minutes)
3. **Fall back to IBKR historical polling** if cache is stale

The bot will automatically use the best available data source.

---

## 📊 How It Works

### Data Flow

```
┌─────────────────────────────────────────────────────────┐
│              DataCollector (Background)                  │
│  • Collects real-time bars from Massive API             │
│  • Stores in SQLite cache (data/cache.db)                │
│  • Updates every 1 minute during market hours            │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│              IBKRDataFeed (Live Trading)                 │
│  Priority 1: Real-time bars from IBKR subscription       │
│  Priority 2: Preloaded bars from buffer                  │
│  Priority 3: Recent bars from Massive cache (< 5 min)     │
│  Priority 4: Historical polling from IBKR (fallback)     │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│              LiveTradingLoop                             │
│  • Processes bars through trading pipeline               │
│  • Executes trades based on agent signals                │
│  • Uses real-time data from Massive API                  │
└─────────────────────────────────────────────────────────┘
```

---

## ✅ Benefits

1. **Real-Time Data Without IBKR Subscription**
   - No need to subscribe to IBKR market data
   - Massive API provides real-time data directly

2. **Automatic Fallback**
   - If IBKR real-time subscription works, uses it
   - If not, uses Massive API cache
   - Always has the best available data source

3. **Cost-Effective**
   - Massive API is typically more affordable than IBKR market data subscriptions
   - Works for both paper and live trading

4. **Reliable**
   - DataCollector continuously updates cache
   - System always has recent data available
   - No dependency on IBKR market data permissions

---

## 🔍 Verification

### Check DataCollector Status

```bash
curl http://localhost:8000/data-collector/status
```

Look for:
- `"api_type": "Massive API"` - Confirms Massive API is being used
- `"is_running": true` - Data collector is active
- Recent `last_collection_times` - Data is being collected

### Check Bot Status

```bash
curl http://localhost:8000/live/status
```

Look for:
- `"last_bar_time"` - Should be recent (within last few minutes during market hours)
- `"bars_collected"` - Should be increasing

### Check Cache

The cache is stored in `data/cache.db`. You can verify it contains recent data:

```python
from services.cache import BarCache
from pathlib import Path

cache = BarCache(Path("data/cache.db"))
bars_df = cache.load("QQQ", "1Min")
print(f"Latest bar: {bars_df.index[-1]}")
print(f"Total bars: {len(bars_df)}")
```

---

## 📝 Notes

- **Market Hours**: DataCollector collects every 1 minute during market hours (9:30 AM - 4:00 PM ET)
- **After Hours**: Collects every 5 minutes outside market hours
- **Cache Freshness**: IBKRDataFeed uses cache if data is within last 5 minutes
- **Automatic**: No manual intervention needed - system automatically uses best data source

---

## 🎉 Status

**✅ COMPLETE - Ready for Live Trading**

The system is now configured to use Massive API for real-time data collection. You can start live trading and the bot will automatically use real-time data from Massive API, bypassing the IBKR market data subscription requirement.

---

## Next Steps

1. **Start DataCollector** (if not already running):
   ```bash
   curl -X POST http://localhost:8000/data-collector/start
   ```

2. **Start Live Trading**:
   - The bot will automatically use Massive API cache for real-time data
   - No IBKR market data subscription needed

3. **Monitor**:
   - Check `/data-collector/status` to verify data collection
   - Check `/live/status` to verify bot is receiving real-time bars

---

**Last Updated:** 2025-12-20  
**Status:** ✅ Production Ready

