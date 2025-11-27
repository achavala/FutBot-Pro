# Offline Trading & Data Collection Guide

This guide explains how to use the trading system during non-trading hours and in offline mode.

## Overview

The system now supports:
- **Continuous data collection** during trading hours
- **Offline trading** using cached data
- **Paper trading** during live trading hours
- **24/7 operation** with cached data

## Features

### 1. Data Collector Service

A background service that continuously collects and stores market data to a local cache database.

**Benefits:**
- Collects data automatically during trading hours
- Stores data locally for offline use
- Works during non-trading hours (collects delayed data)
- Enables offline trading and backtesting

### 2. Cached Data Feed

A data feed implementation that reads from cached data instead of live APIs.

**Benefits:**
- Works offline (no internet required)
- Fast data access (local database)
- Historical data replay
- Perfect for testing and development

### 3. Offline Mode

Run the trading bot using cached data instead of live data feeds.

**Use Cases:**
- Testing strategies during non-trading hours
- Backtesting with historical data
- Development and debugging
- Paper trading with historical data

## Setup

### 1. Start Data Collector

The data collector runs in the background and continuously collects market data.

**Via API:**
```bash
curl -X POST http://localhost:8000/data-collector/start \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["QQQ", "SPY"], "bar_size": "1Min"}'
```

**Via Script:**
```bash
# Start collector for default symbol (QQQ)
python scripts/start_data_collector.py

# Start collector for specific symbols
python scripts/start_data_collector.py QQQ SPY AAPL
```

**Environment Variables:**
- `ALPACA_API_KEY`: Your Alpaca API key (required)
- `ALPACA_SECRET_KEY`: Your Alpaca API secret (required)
- `BAR_SIZE`: Bar size (default: "1Min")

### 2. Check Collector Status

```bash
curl http://localhost:8000/data-collector/status
```

Response:
```json
{
  "is_running": true,
  "symbols": ["QQQ"],
  "bar_size": "1Min",
  "last_collection_times": {
    "QQQ": "2025-11-21T14:30:00"
  },
  "is_trading_hours": true
}
```

### 3. Stop Data Collector

```bash
curl -X POST http://localhost:8000/data-collector/stop
```

## Usage

### Offline Trading

Start the bot in offline mode using cached data:

**Via API:**
```bash
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["QQQ"],
    "broker_type": "paper",
    "offline_mode": true
  }'
```

**Or use cached broker type:**
```bash
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["QQQ"],
    "broker_type": "cached"
  }'
```

### Paper Trading (Live Hours)

During trading hours, use paper trading with live data:

```bash
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["QQQ"],
    "broker_type": "alpaca"
  }'
```

This uses:
- **Live data** from Alpaca API
- **Paper trading** account (no real money)
- **Real-time** market data

## Data Collection Behavior

### During Trading Hours (9:30 AM - 4:00 PM ET)
- Collects data every **1 minute**
- Stores latest bars to cache
- Updates continuously

### Outside Trading Hours
- Collects delayed data every **5 minutes**
- Stores after-hours/pre-market data
- Continues collecting for offline use

## Cache Location

Data is stored in SQLite database:
- **Path**: `data/cache.db` (configurable in `config/settings.yaml`)
- **Format**: SQLite database with bar data
- **Retention**: All collected data is retained

## Troubleshooting

### No Cached Data Available

If you see "No cached data found" error:

1. **Start the data collector:**
   ```bash
   python scripts/start_data_collector.py QQQ
   ```

2. **Wait for data collection** (at least 1 minute during trading hours)

3. **Check cache status:**
   ```bash
   curl http://localhost:8000/data-collector/status
   ```

### Data Collector Not Running

Check if collector is running:
```bash
curl http://localhost:8000/data-collector/status
```

If not running, start it:
```bash
curl -X POST http://localhost:8000/data-collector/start \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["QQQ"]}'
```

### API Keys Missing

Ensure Alpaca API keys are set:
```bash
# Check .env file
cat .env | grep ALPACA
```

Set keys if missing:
```bash
echo "ALPACA_API_KEY=your_key" >> .env
echo "ALPACA_SECRET_KEY=your_secret" >> .env
```

## Best Practices

1. **Start collector before trading hours** to ensure data is available
2. **Run collector continuously** to maintain up-to-date cache
3. **Use offline mode** for testing and development
4. **Use paper trading** during live hours for safe testing
5. **Monitor collector status** regularly to ensure data collection

## API Endpoints

### Data Collector

- `POST /data-collector/start` - Start data collector
- `POST /data-collector/stop` - Stop data collector
- `GET /data-collector/status` - Get collector status

### Live Trading

- `POST /live/start` - Start live trading (supports `offline_mode: true`)
- `POST /live/stop` - Stop live trading
- `GET /live/status` - Get trading status

## Example Workflow

1. **Morning (Before Market Open):**
   ```bash
   # Start data collector
   python scripts/start_data_collector.py QQQ SPY
   ```

2. **During Trading Hours:**
   ```bash
   # Start paper trading with live data
   curl -X POST http://localhost:8000/live/start \
     -H "Content-Type: application/json" \
     -d '{"symbols": ["QQQ"], "broker_type": "alpaca"}'
   ```

3. **After Hours (Testing):**
   ```bash
   # Test with cached data
   curl -X POST http://localhost:8000/live/start \
     -H "Content-Type: application/json" \
     -d '{"symbols": ["QQQ"], "broker_type": "cached"}'
   ```

4. **Monitor:**
   ```bash
   # Check collector status
   curl http://localhost:8000/data-collector/status
   
   # Check trading status
   curl http://localhost:8000/live/status
   ```

## Summary

- ✅ **Data Collector**: Runs continuously, collects and stores data
- ✅ **Offline Mode**: Trade using cached data (no internet required)
- ✅ **Paper Trading**: Safe testing during live hours
- ✅ **24/7 Operation**: Works anytime with cached data

Enjoy trading anytime! 🚀

