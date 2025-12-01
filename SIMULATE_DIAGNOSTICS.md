# Simulate Mode Diagnostics Guide

This guide helps you diagnose why the Simulate button might not be working.

## What Was Fixed

✅ **Broker Client**: Added support for `broker_type="cached"` to use `PaperBrokerClient`  
✅ **Data Feed**: Already correctly handles `broker_type="cached"` → `CachedDataFeed`  
✅ **Logging**: Added comprehensive diagnostic logging throughout the pipeline

## Diagnostic Logging Added

The system now logs at every step:

1. **Request Received**: `🔵 START REQUEST: broker_type=..., offline_mode=..., symbols=...`
2. **Broker Client**: `✅ Using paper broker client for cached/offline simulation`
3. **Data Feed Creation**: `🔵 Creating data feed: broker_type=..., offline_mode=...`
4. **Cache Path**: `🔵 Cache path: /path/to/cache`
5. **Data Feed Created**: `✅ CachedDataFeed created successfully for symbols: [...]`
6. **Live Trading Start**: `🔵 Starting live trading with broker_client=..., data_feed=...`
7. **Bot Manager**: `🔵 Creating LiveTradingLoop with N agents, symbols=...`
8. **Loop Created**: `✅ LiveTradingLoop created successfully`
9. **Loop Start**: `🔵 Calling live_loop.start()...`
10. **Data Feed Connect**: `🔵 [LiveLoop] Connecting data feed...`
11. **Subscribe**: `🔵 [LiveLoop] Subscribing to symbols [...] with preload_bars=100...`
12. **Thread Start**: `✅ [LiveLoop] Background thread started - loop is now running`

## How to Diagnose

### Step 1: Run the Diagnostic Script

```bash
python scripts/diagnose_simulate_mode.py
```

This will:
- Send a test request to `/live/start`
- Show the exact payload
- Display the response
- Tell you what to check next

### Step 2: Check Server Logs

After clicking Simulate or running the diagnostic script, check logs:

```bash
# Local server logs
tail -f /tmp/futbot_server.log

# Or if using Railway, check Railway logs
```

Look for the diagnostic markers (🔵, ✅, ❌) to see where the pipeline stops.

### Step 3: Identify the Failure Point

**If you see:**
- `🔵 START REQUEST` but no `✅ CachedDataFeed created` → Data feed creation failed
- `✅ CachedDataFeed created` but no `🔵 Starting live trading` → Broker client issue
- `🔵 Starting live trading` but no `✅ LiveTradingLoop created` → Loop creation failed
- `✅ LiveTradingLoop created` but no `🔵 [LiveLoop] Starting` → Loop start failed
- `🔵 [LiveLoop] Starting` but no `✅ [LiveLoop] Background thread started` → Thread creation failed

### Step 4: Common Issues

#### Issue 1: No Cached Data

**Symptoms:**
- Log shows: `No cached data found for QQQ`
- Log shows: `Only 0 bars loaded for QQQ`

**Solution:**
```bash
# Start data collector first
curl -X POST http://localhost:8000/data-collector/start \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["QQQ", "SPY"], "bar_size": "1Min"}'

# Wait a few minutes for data to collect, then try Simulate again
```

#### Issue 2: Cache Path Not Found

**Symptoms:**
- Error: `Failed to create cached data feed: [Errno 2] No such file or directory`

**Solution:**
- Check `config/settings.yaml` - verify `data.cache.path` exists
- Create the cache directory if needed

#### Issue 3: Data Feed Connection Fails

**Symptoms:**
- Log shows: `❌ Failed to create CachedDataFeed: ...`

**Solution:**
- Check cache database file exists and is readable
- Verify cache path in settings

#### Issue 4: Loop Thread Never Starts

**Symptoms:**
- Log shows: `✅ live_loop.start() completed` but no `✅ [LiveLoop] Background thread started`

**Solution:**
- Check for exceptions in logs
- Verify data feed has data (empty data feed can cause silent failures)

## Expected Log Flow (Success)

When Simulate works correctly, you should see:

```
🔵 START REQUEST: broker_type=cached, offline_mode=True, symbols=['QQQ', 'SPY']
✅ Using paper broker client for cached/offline simulation
🔵 Creating data feed: broker_type=cached, offline_mode=True
🔵 Cache path: /Users/chavala/FutBot/data/cache.db
✅ CachedDataFeed created successfully for symbols: ['QQQ', 'SPY']
🔵 Starting live trading with broker_client=PaperBrokerClient, data_feed=CachedDataFeed
🔵 LiveTradingConfig created, calling bot_manager.start_live_trading()...
🔵 Creating LiveTradingLoop with 4 agents, symbols=['QQQ', 'SPY']
✅ LiveTradingLoop created successfully
🔵 Calling live_loop.start()...
🔵 [LiveLoop] Starting live trading loop...
🔵 [LiveLoop] Data feed connected: False
🔵 [LiveLoop] Connecting data feed...
✅ [LiveLoop] Data feed connected successfully
🔵 [LiveLoop] Subscribing to symbols ['QQQ', 'SPY'] with preload_bars=100...
Loading cached data for QQQ...
Loaded 500 cached bars for QQQ
Loading cached data for SPY...
Loaded 500 cached bars for SPY
✅ [LiveLoop] Subscribe result: True
Loaded 100 bars for QQQ (preloaded: 100)
Loaded 100 bars for SPY (preloaded: 100)
🔵 [LiveLoop] Creating background thread for _run_loop...
✅ [LiveLoop] Background thread started - loop is now running
✅ live_loop.start() completed - loop thread should be running
✅ Bot state set to running=True
✅ bot_manager.start_live_trading() completed successfully
```

## Next Steps

1. **Run the diagnostic script** to see the exact error
2. **Check logs** for where the pipeline stops
3. **Share the logs** (filtered for errors) if you need help

The diagnostic logging will pinpoint exactly where the simulation fails!


