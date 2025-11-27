# Collect 3 Months of Historical Data for Offline Testing

**Goal:** Collect last 3 months of historical data for stocks, crypto, and options to enable offline testing during market closure.

---

## Quick Start

### Option 1: Automated Script (Recommended)

```bash
# Set your API keys (if not already in .env)
export POLYGON_API_KEY="your_polygon_key"  # Better for historical data
# OR
export ALPACA_API_KEY="your_alpaca_key"
export ALPACA_SECRET_KEY="your_alpaca_secret"

# Run collection script
bash scripts/collect_3months_data.sh
```

### Option 2: Python Script with Custom Options

```bash
# Collect 3 months of data
python3 scripts/collect_historical_data.py \
  --months 3 \
  --stocks SPY QQQ \
  --crypto BTC/USD \
  --options SPY \
  --use-polygon  # Use Polygon API (better for historical)
```

---

## What Gets Collected

### 1. Stock Data
- **Symbols:** SPY, QQQ (configurable)
- **Timeframe:** 1-minute bars
- **Duration:** Last 3 months
- **Storage:** `cache/bars/SPY_1min_*.parquet`

### 2. Crypto Data
- **Symbols:** BTC/USD (configurable)
- **Timeframe:** 1-minute bars
- **Duration:** Last 3 months
- **Storage:** `cache/bars/BTC_USD_1min_*.parquet`

### 3. Options Data
- **Underlying:** SPY (configurable)
- **Type:** PUT and CALL contracts
- **Storage:** Options chain metadata (current contracts)

---

## Detailed Usage

### Basic Collection

```bash
python3 scripts/collect_historical_data.py --months 3
```

This collects:
- SPY and QQQ stock data
- BTC/USD crypto data
- SPY options chains

### Custom Symbols

```bash
python3 scripts/collect_historical_data.py \
  --months 3 \
  --stocks SPY QQQ AAPL TSLA \
  --crypto BTC/USD ETH/USD \
  --options SPY QQQ
```

### Using Polygon API (Recommended)

Polygon API is better for historical data collection:

```bash
# Set Polygon API key
export POLYGON_API_KEY="your_key"

# Collect with Polygon
python3 scripts/collect_historical_data.py \
  --months 3 \
  --use-polygon
```

**Benefits:**
- More reliable historical data
- Better rate limits
- More complete data coverage

### Skip Options Data

If you don't need options data:

```bash
python3 scripts/collect_historical_data.py \
  --months 3 \
  --skip-options
```

---

## API Requirements

### Polygon API (Recommended)
- **Key:** `POLYGON_API_KEY` environment variable
- **Plan:** Free tier allows historical data
- **Rate Limits:** 5 requests/second (free tier)

### Alpaca API (Alternative)
- **Keys:** `ALPACA_API_KEY` and `ALPACA_SECRET_KEY`
- **Plan:** Paper trading account works
- **Rate Limits:** Varies by plan

---

## Collection Process

### Step 1: Check Prerequisites

```bash
# Check API keys
echo $POLYGON_API_KEY  # or
echo $ALPACA_API_KEY

# Check cache directory
ls -la cache/bars/
```

### Step 2: Run Collection

```bash
# Quick start
bash scripts/collect_3months_data.sh

# Or detailed
python3 scripts/collect_historical_data.py --months 3 --use-polygon
```

### Step 3: Monitor Progress

The script will show:
- Progress for each symbol
- Number of bars collected
- Any errors encountered

**Example output:**
```
Collecting 3 months of stock data for: ['SPY', 'QQQ']
Date range: 2024-10-15 to 2025-01-15
Collecting data for SPY...
✅ Stored 39000 bars for SPY
Collecting data for QQQ...
✅ Stored 39000 bars for QQQ
✅ Stock data collection complete: 78000 total bars
```

### Step 4: Verify Data

```bash
# Test offline capabilities
python3 scripts/test_offline_trading.py

# Check cache files
ls -lh cache/bars/

# Check file sizes (should be substantial)
du -sh cache/bars/
```

---

## Expected Data Volume

### 3 Months of 1-Minute Bars

**Per Symbol:**
- Trading days: ~63 days (3 months)
- Trading hours per day: 6.5 hours
- Minutes per day: 390 minutes
- **Total bars per symbol: ~24,570 bars**

**For SPY + QQQ + BTC/USD:**
- **Total: ~73,710 bars**
- **Estimated cache size: 50-100 MB**

---

## Storage Location

Data is stored in:
```
cache/
└── bars/
    ├── SPY_1min_2024-10-15.parquet
    ├── SPY_1min_2024-10-16.parquet
    ├── QQQ_1min_2024-10-15.parquet
    ├── BTC_USD_1min_2024-10-15.parquet
    └── ...
```

---

## Troubleshooting

### Issue: No API Keys

**Error:** `POLYGON_API_KEY not found` or `ALPACA_API_KEY not found`

**Solution:**
```bash
# Add to .env file
echo "POLYGON_API_KEY=your_key" >> .env
# OR
echo "ALPACA_API_KEY=your_key" >> .env
echo "ALPACA_SECRET_KEY=your_secret" >> .env

# Reload
source .env
```

### Issue: Rate Limiting

**Error:** `429 Too Many Requests`

**Solution:**
- Script includes delays for Polygon API
- For Alpaca, reduce number of symbols
- Run collection during off-peak hours

### Issue: Missing Data

**Symptoms:** Some dates missing bars

**Solution:**
- Check if market was closed (holidays, weekends)
- Verify API key permissions
- Try Polygon API (more reliable)

### Issue: Options Data Not Available

**Symptoms:** No options chains collected

**Solution:**
- Options data may not be available historically
- Current options chains are collected
- Historical options data requires premium APIs

---

## Verification

### Check Data Availability

```bash
# Run offline test
python3 scripts/test_offline_trading.py
```

**Expected output:**
```
Testing SPY...
  ✅ Found 24570 cached bars
  ✅ get_latest_bars() works: 10 bars
  ✅ get_historical_bars() works: 24570 bars

Testing QQQ...
  ✅ Found 24570 cached bars
  ✅ get_latest_bars() works: 10 bars
  ✅ get_historical_bars() works: 24570 bars

Testing BTC/USD...
  ✅ Found 24570 cached bars
  ✅ get_latest_bars() works: 10 bars
  ✅ get_historical_bars() works: 24570 bars
```

### Check Cache Size

```bash
# Check total cache size
du -sh cache/bars/

# Count files
find cache/bars/ -name "*.parquet" | wc -l

# Check latest data
ls -lt cache/bars/ | head -10
```

---

## Usage After Collection

### Start Offline Trading

```bash
# Use cached data feed
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["SPY"],
    "use_cached": true
  }'
```

### Test Strategies

```bash
# Run backtests with collected data
python -m backtesting.runner \
  --data cache/bars/ \
  --symbol SPY \
  --start 2024-10-15 \
  --end 2025-01-15
```

---

## Best Practices

1. **Collect Before Market Closes**
   - Run collection script before market closes
   - Ensures you have latest data

2. **Use Polygon API**
   - More reliable for historical data
   - Better rate limits
   - More complete coverage

3. **Verify Data**
   - Always run `test_offline_trading.py` after collection
   - Check cache file sizes
   - Verify date ranges

4. **Monitor Collection**
   - Watch for errors in logs
   - Check API rate limits
   - Verify all symbols collected

5. **Backup Cache**
   - Copy `cache/bars/` directory
   - Useful if cache gets corrupted
   - Can restore for offline testing

---

## Summary

✅ **Collection Script:** `scripts/collect_historical_data.py`  
✅ **Quick Start:** `bash scripts/collect_3months_data.sh`  
✅ **Data Storage:** `cache/bars/`  
✅ **Verification:** `python3 scripts/test_offline_trading.py`  

**You now have 3 months of data for offline testing!** 🚀

