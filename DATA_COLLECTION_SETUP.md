# Data Collection Setup for Offline Testing

This guide explains how to set up continuous data collection so you can test the bot offline during non-trading hours.

## Quick Start

### 1. Start Data Collector (Recommended)

**Option A: Via Script (Easiest)**
```bash
# Start collector for QQQ and SPY
./scripts/ensure_data_collector_running.sh
```

**Option B: Via API**
```bash
curl -X POST http://localhost:8000/data-collector/start \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["QQQ", "SPY"], "bar_size": "1Min"}'
```

**Option C: Via Python Script**
```bash
python scripts/start_data_collector.py QQQ SPY
```

### 2. Verify Collector is Running

```bash
curl http://localhost:8000/data-collector/status | python3 -m json.tool
```

Expected response:
```json
{
  "is_running": true,
  "symbols": ["QQQ", "SPY"],
  "bar_size": "1Min",
  "last_collection_times": {
    "QQQ": "2025-11-25T14:30:00",
    "SPY": "2025-11-25T14:30:00"
  },
  "is_trading_hours": true
}
```

## How It Works

### Collection Schedule

- **During Trading Hours (9:30 AM - 4:00 PM ET)**: Collects data every **1 minute**
- **Outside Trading Hours**: Collects data every **5 minutes** (for after-hours/pre-market data)
- **Weekends**: Still collects delayed data every 5 minutes

### Data Storage

- Data is stored in: `data/cache.db` (SQLite database)
- Each bar includes: timestamp, open, high, low, close, volume
- Data persists across restarts

### Offline Trading

Once data is collected, you can trade offline:

```bash
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["QQQ"],
    "broker_type": "cached",
    "fixed_investment_amount": 1000
  }'
```

## Requirements

### Environment Variables

Make sure these are set in your `.env` file:

```bash
ALPACA_API_KEY=your_api_key
ALPACA_SECRET_KEY=your_secret_key
```

### API Server Must Be Running

The data collector endpoints require the FastAPI server:

```bash
python main.py --mode api --port 8000
```

## Monitoring

### Check Collector Status

```bash
curl http://localhost:8000/data-collector/status | python3 -m json.tool
```

### Check Cache Size

```bash
# Check database file size
ls -lh data/cache.db

# Or use SQLite to query
sqlite3 data/cache.db "SELECT COUNT(*) FROM bars WHERE symbol='QQQ';"
```

### View Collection Logs

```bash
tail -f logs/api_server.log | grep -i "collector\|collected"
```

## Troubleshooting

### Collector Not Starting

**Error: "Alpaca API keys required"**
- Check `.env` file has `ALPACA_API_KEY` and `ALPACA_SECRET_KEY`
- Restart API server after adding keys

**Error: "Data collector already running"**
- Collector is already active
- Check status: `curl http://localhost:8000/data-collector/status`

### No Data Being Collected

**Check API keys:**
```bash
echo $ALPACA_API_KEY
echo $ALPACA_SECRET_KEY
```

**Check collector logs:**
```bash
tail -50 logs/api_server.log | grep -i error
```

**Verify trading hours:**
- Collector runs slower (5 min) outside trading hours
- Check `is_trading_hours` in status response

### Offline Trading Not Working

**Error: "No bars found in cache"**
- Wait for collector to gather at least 30-50 bars
- Check cache: `sqlite3 data/cache.db "SELECT COUNT(*) FROM bars WHERE symbol='QQQ';"`
- Start collector and wait a few minutes

**Error: "Cache path not found"**
- Ensure `data/` directory exists
- Check `config/settings.yaml` for cache path

## Best Practices

1. **Start collector before trading hours** to ensure data is available
2. **Run collector continuously** - it's lightweight and won't impact performance
3. **Collect multiple symbols** - QQQ, SPY, etc. for flexibility
4. **Monitor cache size** - SQLite database grows over time (can be cleaned if needed)
5. **Use offline mode for testing** - Test strategies without risking real money

## Auto-Start on System Boot

To automatically start the data collector when your system boots:

### Linux (systemd)

Create `/etc/systemd/system/futbot-collector.service`:

```ini
[Unit]
Description=FutBot Data Collector
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/FutBot
Environment="PATH=/path/to/FutBot/.venv/bin"
ExecStart=/path/to/FutBot/.venv/bin/python scripts/start_data_collector.py QQQ SPY
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable futbot-collector
sudo systemctl start futbot-collector
```

### macOS (launchd)

Create `~/Library/LaunchAgents/com.futbot.collector.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.futbot.collector</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/FutBot/.venv/bin/python</string>
        <string>/path/to/FutBot/scripts/start_data_collector.py</string>
        <string>QQQ</string>
        <string>SPY</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/path/to/FutBot</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

Load:
```bash
launchctl load ~/Library/LaunchAgents/com.futbot.collector.plist
```

## Summary

✅ **Start collector**: `./scripts/ensure_data_collector_running.sh`  
✅ **Check status**: `curl http://localhost:8000/data-collector/status`  
✅ **Trade offline**: Use `broker_type: "cached"` in `/live/start`  
✅ **Monitor**: Check logs and cache size regularly

The data collector ensures you always have fresh data for offline testing! 📊

