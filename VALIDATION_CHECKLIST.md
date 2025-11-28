# Server Restart Validation Checklist

## ✅ All Fixes Applied

1. ✅ Synthetic bar fallback in `get_next_bar()` 
2. ✅ Synthetic bar fallback in `get_next_n_bars()`
3. ✅ Synthetic bar fallback in loop
4. ✅ `bars_per_symbol` updated during preload
5. ✅ Symbol case normalization (SPY not spy)
6. ✅ Version endpoint added (`/version`)
7. ✅ Enhanced logging for debugging

## 🚀 RESTART SERVER NOW

```bash
# Find and kill server
ps aux | grep "python.*main.py\|uvicorn" | grep -v grep
kill <PID>

# Restart
cd /Users/chavala/FutBot
./start_server.sh
```

## 🔍 Validation Steps

### Step 1: Check Version Endpoint

```bash
curl http://localhost:8000/version
```

**Expected:**
```json
{
  "version": "1.0.0",
  "build_date": "2024-11-28",
  "features": [
    "synthetic_bar_fallback",
    "bars_per_symbol_preload_fix",
    "testing_mode",
    "aggressive_logging",
    "symbol_case_normalization"
  ],
  "status": "ready"
}
```

If you see this → ✅ New code is loaded!

### Step 2: Start Trading

```bash
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["SPY"],
    "broker_type": "cached",
    "offline_mode": true,
    "testing_mode": true,
    "replay_speed": 600.0
  }'
```

### Step 3: Watch Logs

```bash
tail -f /tmp/futbot_server.log | grep -E "LiveLoop|bars_per_symbol|synthetic|OFFLINE MODE"
```

**Expected logs:**
```
🔵 [LiveLoop] OFFLINE MODE ENABLED
🔵 [LiveLoop] Data feed: CachedDataFeed, synthetic_enabled: True
🔵 [LiveLoop] Testing mode: True, min bars: 1
🔵 [LiveLoop] Got 10 batch bars for SPY
✅ [LiveLoop] SPY bars_per_symbol = 10
✅ [LiveLoop] Current state: bar_count=10, bars_per_symbol={'SPY': 10}
```

### Step 4: Check Status (within 5 seconds)

```bash
curl -s http://localhost:8000/live/status | python3 -m json.tool
```

**Expected:**
```json
{
  "is_running": true,
  "mode": "offline",
  "bars_per_symbol": {
    "SPY": 10
  },
  "bar_count": 10
}
```

If `bars_per_symbol["SPY"] > 0` → ✅ **SUCCESS!**

### Step 5: Run Validation Script

```bash
./scripts/validate_server_restart.sh
```

This script will:
- Check server is running
- Verify version endpoint
- Check logs for synthetic fallback
- Start trading
- Verify `bars_per_symbol` updates
- Report success/failure

## 🎯 Success Criteria

After restart, within 5 seconds you should see:

1. ✅ `/version` endpoint returns new features
2. ✅ Logs show "synthetic_enabled: True"
3. ✅ Logs show "Got X batch bars for SPY"
4. ✅ `bars_per_symbol["SPY"] > 0` in status
5. ✅ Trades start executing (with testing_mode, needs only 1 bar)

## ⚠️ If Still Not Working

1. **Check server process:**
   ```bash
   ps aux | grep python | grep -v grep
   ```
   Make sure old process is killed.

2. **Check logs for errors:**
   ```bash
   tail -n 200 /tmp/futbot_server.log | grep -E "Error|Exception|Traceback"
   ```

3. **Verify code is updated:**
   ```bash
   git log --oneline -5
   ```
   Should see latest commits.

4. **Hard restart:**
   ```bash
   pkill -9 python
   sleep 2
   ./start_server.sh
   ```

## Summary

All code fixes are in place. **The critical step is restarting the server** to load the new code. Once restarted, bars should flow immediately and `bars_per_symbol` will update correctly.

