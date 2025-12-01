# Fix "Insufficient Bars for Analysis" Issue

## 🔍 Problem

The system requires **at least 30 bars** for regime analysis. If you see "Insufficient bars for analysis", it means you don't have enough historical data cached.

## ✅ Solutions

### Solution 1: Start a Simulation (Easiest)

The simulation will automatically generate synthetic bars if no cached data exists:

1. **Select Symbol**: Choose SPY or QQQ
2. **Set Time Window**: 
   - Start Time: Choose a date (e.g., 3 months ago)
   - End Time: Choose a later date
3. **Set Speed**: Choose 600x for fast collection
4. **Click "Simulate"**

The simulation will:
- Generate synthetic bars if cache is empty
- Process bars until you have 30+ bars
- Then start showing trade setups

**Time**: ~5-10 seconds at 600x speed

---

### Solution 2: Collect Real Historical Data (Recommended)

#### Option A: Using Data Collector Script

```bash
# Make sure you have API keys set
export ALPACA_API_KEY="your_key"
export ALPACA_SECRET_KEY="your_secret"

# Or use Polygon (better for historical data)
export POLYGON_API_KEY="your_polygon_key"

# Run collection script
python3 scripts/collect_historical_data.py \
  --symbols SPY QQQ \
  --months 3 \
  --timeframe 1Min
```

#### Option B: Using API Endpoint

```bash
# Start data collector via API
curl -X POST http://localhost:8000/data-collector/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["SPY", "QQQ"],
    "bar_size": "1Min",
    "lookback_days": 90
  }'
```

#### Option C: Manual Collection Script

Create a simple script:

```python
from services.data_collector import DataCollector
from pathlib import Path

collector = DataCollector(
    symbols=["SPY", "QQQ"],
    bar_size="1Min",
    cache_path=Path("data/cache.db")
)

# Collect last 3 months
collector.collect_historical(days=90)
```

---

### Solution 3: Check Current Bar Count

Check how many bars you currently have:

```bash
# Check via API
curl http://localhost:8000/live/status | python3 -m json.tool

# Look for:
# "bar_count": X
# "bars_per_symbol": {"SPY": X, "QQQ": Y}
```

Or check the Status tab in the Performance panel - it now shows:
- Current bar count
- Progress bar (X/30 bars)
- How many more bars are needed

---

### Solution 4: Lower the Threshold (Temporary)

If you want to test with fewer bars, you can temporarily lower the requirement:

**File**: `core/live/scheduler.py` (line 405)

```python
# Change from:
if len(bars_df) < 30:

# To:
if len(bars_df) < 10:  # Lower threshold for testing
```

**⚠️ Warning**: Lower thresholds may produce less accurate analysis.

---

## 📊 Understanding Bar Requirements

### Why 30 Bars?

- **Technical Indicators**: Need history for:
  - EMA (9 periods)
  - SMA (20 periods)
  - RSI (14 periods)
  - ATR (14 periods)
  - ADX (14 periods)
  - VWAP (session-based)
  - Hurst Exponent (100 periods, but works with 20+)
  - Rolling Regression (30 periods)

- **Minimum**: 30 bars ensures all indicators have valid values
- **Recommended**: 50+ bars for more stable analysis

### Bar Count by Timeframe

- **1-minute bars**: 30 bars = 30 minutes of data
- **5-minute bars**: 30 bars = 2.5 hours of data
- **1-hour bars**: 30 bars = 30 hours (1.25 days) of data

---

## 🚀 Quick Fix Steps

### Fastest Method (30 seconds):

1. **Open Dashboard**
2. **Select**: SPY, Start Time (3 months ago), End Time (now), Speed (600x)
3. **Click "Simulate"**
4. **Wait**: ~5-10 seconds for 30+ bars
5. **Check Status Tab**: Should show "GOOD SETUP" or "CAUTION" instead of "Waiting for Data"

### If Simulation Doesn't Generate Bars:

1. **Check Logs**: `tail -f /tmp/futbot_server.log`
2. **Look for**: "Generated X synthetic bars"
3. **If no synthetic bars**: Check `CachedDataFeed._generate_synthetic_bars()` is working
4. **Alternative**: Use Solution 2 to collect real data

---

## 🔧 Troubleshooting

### Issue: Simulation starts but no bars are processed

**Check**:
```bash
# Check if simulation is running
curl http://localhost:8000/live/status

# Check logs
tail -f /tmp/futbot_server.log | grep -i "bar\|process"
```

**Fix**: Ensure time window has valid dates and simulation is actually running.

---

### Issue: Bars are processed but still shows "Insufficient"

**Check**:
- Bar count in status: Should be >= 30
- Regime validity: Check `/regime` endpoint
- Feature computation: Check if indicators are calculating

**Fix**: Wait a few more seconds for bars to accumulate, or check if there's an error in feature computation.

---

### Issue: No cached data and synthetic bars not generating

**Check**:
```python
# In Python console
from services.cache import BarCache
from pathlib import Path

cache = BarCache(Path("data/cache.db"))
bars = cache.load("SPY", "1Min")
print(f"Bars in cache: {len(bars)}")
```

**Fix**: 
- Ensure cache database exists
- Check file permissions
- Try collecting data manually (Solution 2)

---

## 📈 Status Tab Shows Progress

The Status tab now displays:
- **Current Bar Count**: X/30 bars
- **Progress Bar**: Visual indicator
- **Status**: COLLECTING / NO DATA / READY
- **Suggestion**: What to do next

This makes it easy to see when you have enough bars!

---

## ✅ Verification

After collecting bars, verify:

1. **Status Tab** shows bar count >= 30
2. **Trade Setups** shows "GOOD SETUP", "CAUTION", or "AVOID" (not "Waiting for Data")
3. **Regime** shows valid regime type (not "COMPRESSION" with 0% confidence)
4. **Agent Activity** shows agents with weights > 0%

---

**Last Updated**: Current
**Minimum Bars Required**: 30
**Recommended**: 50+ for stable analysis


