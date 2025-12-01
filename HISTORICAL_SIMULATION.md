# Historical Simulation Guide

This guide explains how to run offline trading simulations starting from a specific historical date.

## Overview

You can now simulate trading starting from any date in the past (up to 2 months or whatever data you have cached). This is perfect for:
- Testing strategies on historical data
- Replaying specific market periods
- Backtesting with realistic data
- Learning from past market conditions

## How It Works

When you specify a `start_date`, the system will:
1. Load all cached data from that date onwards
2. Replay the market data chronologically
3. Execute trades based on historical prices
4. Show you how your strategy would have performed

## Usage

### Method 1: Via Dashboard (Easiest)

1. **Open the dashboard** at `http://localhost:8000/`
2. **Enter a start date** in the date picker next to the "Simulate" button
   - Format: `YYYY-MM-DD` (e.g., `2024-01-15`)
   - Leave empty to use all available data
3. **Click "Simulate"**
4. The simulation will start from that date and replay forward

### Method 2: Via API

```bash
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["QQQ", "SPY"],
    "broker_type": "cached",
    "offline_mode": true,
    "start_date": "2024-01-15",
    "fixed_investment_amount": 10000.0
  }'
```

**Parameters:**
- `start_date`: Date in `YYYY-MM-DD` format (optional)
  - If provided, simulation starts from market open (9:30 AM ET) on that date
  - If omitted, uses all available cached data
- `symbols`: List of symbols to trade
- `broker_type`: Must be `"cached"` for offline simulation
- `offline_mode`: Set to `true` for offline trading

## Date Format

- **Format**: `YYYY-MM-DD` (e.g., `2024-01-15`)
- **Time**: Automatically set to market open (9:30 AM ET = 13:30 UTC)
- **Timezone**: UTC (converted from ET)

## Examples

### Example 1: Start from January 15, 2024

```bash
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["QQQ"],
    "broker_type": "cached",
    "start_date": "2024-01-15"
  }'
```

### Example 2: Start from 2 months ago

```bash
# Calculate date 2 months ago (bash)
START_DATE=$(date -v-2m +%Y-%m-%d)

curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d "{
    \"symbols\": [\"QQQ\", \"SPY\"],
    \"broker_type\": \"cached\",
    \"start_date\": \"$START_DATE\"
  }"
```

### Example 3: Use all available data (no start_date)

```bash
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["QQQ"],
    "broker_type": "cached"
  }'
```

## Data Requirements

### You Need Cached Data

The simulation requires cached data for the symbols you want to trade:

1. **Check if you have data:**
   ```bash
   curl http://localhost:8000/data-collector/status
   ```

2. **If no data, collect it first:**
   ```bash
   # Start data collector
   curl -X POST http://localhost:8000/data-collector/start \
     -H "Content-Type: application/json" \
     -d '{"symbols": ["QQQ", "SPY"], "bar_size": "1Min"}'
   
   # Wait for data collection (at least a few minutes)
   ```

3. **Or download historical data:**
   - Use the data collector to backfill historical data
   - Or import data from CSV files

### Data Availability

- **Minimum**: Need at least 50 bars to start trading
- **Recommended**: 500+ bars for meaningful simulation
- **Time Range**: Can simulate any date range you have cached

## How It Works Internally

1. **Date Parsing**: Converts `YYYY-MM-DD` to datetime at market open (9:30 AM ET)
2. **Data Loading**: Loads all bars from `start_date` onwards from cache
3. **Chronological Replay**: Replays bars in order, one minute at a time
4. **Trading Execution**: Executes trades based on historical prices
5. **Performance Tracking**: Tracks P&L, positions, and metrics

## Limitations

1. **Data Availability**: Can only simulate dates you have cached
2. **No Future Data**: Can't use future data (obviously)
3. **Market Hours**: Starts at market open (9:30 AM ET) on the specified date
4. **Real-time Speed**: Replays at real-time speed (1 bar = 1 minute)

## Tips

1. **Collect Data First**: Make sure you have data for the date range you want
2. **Start Dates**: Use weekdays (markets are closed on weekends)
3. **Data Range**: The more data you have, the longer you can simulate
4. **Multiple Symbols**: All symbols start from the same date

## Troubleshooting

### "No cached data found for [symbol]"

**Solution**: Collect data first or use a date where you have data

```bash
# Check what dates you have data for
# (You may need to query the cache directly)
```

### "Only 0 bars loaded"

**Solution**: 
- Check if you have data for that date
- Try a different start date
- Collect more data

### "Invalid start_date format"

**Solution**: Use `YYYY-MM-DD` format (e.g., `2024-01-15`)

## Advanced: Multiple Date Ranges

To test different periods, run multiple simulations:

```bash
# Test January 2024
curl -X POST http://localhost:8000/live/start \
  -d '{"symbols": ["QQQ"], "broker_type": "cached", "start_date": "2024-01-15"}'

# Stop and test February 2024
curl -X POST http://localhost:8000/live/stop

curl -X POST http://localhost:8000/live/start \
  -d '{"symbols": ["QQQ"], "broker_type": "cached", "start_date": "2024-02-15"}'
```

## Summary

✅ **Start from any date** you have cached data for  
✅ **Replay historical markets** chronologically  
✅ **Test strategies** on real historical data  
✅ **Learn from past** market conditions  

Just specify `start_date` in `YYYY-MM-DD` format and the simulation will start from that date!


