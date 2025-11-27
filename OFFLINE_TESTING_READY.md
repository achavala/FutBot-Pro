# Offline Testing Preparation Guide

**Goal:** Ensure system is ready to test and work offline for the next 4 days while stock market is closed.

---

## Quick Start

### Step 1: Prepare System

```bash
# Run preparation script
bash scripts/prepare_offline_testing.sh
```

This will:
- ✅ Check API server
- ✅ Create necessary directories
- ✅ Check data availability
- ✅ Verify cached data feed
- ✅ Create offline config

### Step 2: Start Data Collection (Before Market Closes)

```bash
# Start data collector to gather data
python3 scripts/start_data_collector.py --symbols SPY QQQ --duration 24
```

Or run in background:
```bash
nohup python3 scripts/start_data_collector.py --symbols SPY QQQ --duration 24 > logs/data_collector.log 2>&1 &
```

### Step 3: Test Offline Capabilities

```bash
# Test that cached data feed works
python3 scripts/test_offline_trading.py
```

---

## Detailed Steps

### 1. Before Market Closes

**Collect data for offline use:**

```bash
# Option 1: Run data collector script
python3 scripts/start_data_collector.py \
  --symbols SPY QQQ BTC/USD \
  --duration 8 \
  --interval 60

# Option 2: Use API endpoint (if available)
curl -X POST http://localhost:8000/data/collector/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["SPY", "QQQ"],
    "duration_hours": 8
  }'
```

**Monitor data collection:**
```bash
tail -f logs/data_collector.log
# Or
tail -f logs/*.log | grep -i "collect\|cache"
```

**Check cached data:**
```bash
ls -lh cache/bars/
# Should see files like:
# SPY_1min_2025-01-*.parquet
# QQQ_1min_2025-01-*.parquet
```

### 2. Verify Offline Capabilities

**Test cached data feed:**
```bash
python3 scripts/test_offline_trading.py
```

**Expected output:**
```
============================================================
TESTING OFFLINE TRADING CAPABILITIES
============================================================

Testing SPY...
  ✅ Found 480 cached bars
  ✅ get_latest_bars() works: 10 bars
  ✅ get_historical_bars() works: 480 bars

Testing QQQ...
  ✅ Found 480 cached bars
  ✅ get_latest_bars() works: 10 bars
  ✅ get_historical_bars() works: 480 bars

============================================================
OFFLINE TESTING COMPLETE
============================================================
```

### 3. Start Offline Trading

**Option 1: Use CachedDataFeed directly**

```python
from core.live.data_feed_cached import CachedDataFeed

# Create cached feed
feed = CachedDataFeed(symbols=["SPY", "QQQ"])

# Use in trading loop
# The scheduler will automatically use cached data when online feed fails
```

**Option 2: Configure for offline mode**

```bash
# Set environment variable
export OFFLINE_MODE=true
export USE_CACHED_DATA=true

# Start trading
python main.py --mode api --port 8000
```

**Option 3: Use API with cached flag**

```bash
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["SPY"],
    "use_cached": true
  }'
```

---

## System Components for Offline Mode

### 1. CachedDataFeed

**Location:** `core/live/data_feed_cached.py`

**Features:**
- ✅ Reads from local cache
- ✅ Implements DataFeed protocol
- ✅ Works offline (no API calls)
- ✅ Falls back gracefully

**Usage:**
```python
from core.live.data_feed_cached import CachedDataFeed

feed = CachedDataFeed(symbols=["SPY"])
bars = feed.get_latest_bars("SPY", "1min", 10)
```

### 2. BarCache

**Location:** `core/cache/bar_cache.py`

**Features:**
- ✅ Stores bars in Parquet format
- ✅ Efficient storage and retrieval
- ✅ Time-based queries
- ✅ Symbol and timeframe organization

**Usage:**
```python
from core.cache.bar_cache import BarCache

cache = BarCache()
bars = cache.load(symbol="SPY", timeframe="1min", start=None, end=None)
```

### 3. Data Collector

**Location:** `scripts/start_data_collector.py`

**Features:**
- ✅ Collects data continuously
- ✅ Stores in cache automatically
- ✅ Configurable duration and interval
- ✅ Multiple symbols support

---

## Directory Structure

```
FutBot/
├── cache/
│   └── bars/
│       ├── SPY_1min_2025-01-15.parquet
│       ├── QQQ_1min_2025-01-15.parquet
│       └── ...
├── data/
│   └── offline_config.json
└── logs/
    └── data_collector.log
```

---

## Monitoring During Offline Testing

### Check Data Availability

```bash
# Count cached bars
find cache/bars/ -name "*.parquet" | wc -l

# Check file sizes
ls -lh cache/bars/

# Check latest data
ls -lt cache/bars/ | head -10
```

### Monitor Trading Logs

```bash
# Watch for cached data usage
tail -f logs/*.log | grep -i "cached\|cache\|offline"

# Watch for errors
tail -f logs/*.log | grep -i "error\|fail"
```

### Check System Status

```bash
# API health
curl http://localhost:8000/health

# Regime status
curl http://localhost:8000/regime

# Trading status
curl http://localhost:8000/live/status
```

---

## Troubleshooting

### Issue: No Cached Data

**Symptoms:**
- `test_offline_trading.py` shows "No cached data"
- `cache/bars/` directory is empty

**Solutions:**
1. Run data collector before market closes
2. Check data collector logs for errors
3. Verify API credentials are set
4. Check network connectivity

### Issue: CachedDataFeed Not Working

**Symptoms:**
- Import errors
- No bars returned

**Solutions:**
1. Check cache directory exists
2. Verify bar files are in correct format
3. Check symbol names match (SPY vs SPY/USD)
4. Review `core/live/data_feed_cached.py` logs

### Issue: Trading Loop Not Using Cached Data

**Symptoms:**
- Trading stops when market closes
- Errors about API connectivity

**Solutions:**
1. Ensure `CachedDataFeed` is configured
2. Check scheduler uses cached feed as fallback
3. Set `OFFLINE_MODE=true` environment variable
4. Verify `use_cached` flag is set

---

## Success Criteria

**System is ready for offline testing when:**

1. ✅ Data collector has gathered data (check `cache/bars/`)
2. ✅ `test_offline_trading.py` passes all tests
3. ✅ CachedDataFeed can load and serve bars
4. ✅ Trading loop can run with cached data
5. ✅ No API connectivity errors in logs

---

## Next Steps After Market Reopens

1. **Switch back to live data feed**
   ```bash
   unset OFFLINE_MODE
   unset USE_CACHED_DATA
   ```

2. **Continue data collection**
   - Keep data collector running
   - Maintain cache for future offline testing

3. **Review offline test results**
   - Check logs for any issues
   - Compare offline vs online behavior
   - Update configurations as needed

---

## Quick Reference

```bash
# Prepare system
bash scripts/prepare_offline_testing.sh

# Start data collection
python3 scripts/start_data_collector.py --symbols SPY QQQ --duration 24

# Test offline
python3 scripts/test_offline_trading.py

# Check cached data
ls -lh cache/bars/

# Monitor logs
tail -f logs/*.log | grep -i "cached\|collect"
```

---

**System is now ready for offline testing!** 🚀

