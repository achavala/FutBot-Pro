# Replay Engine Validation & Optimizations

## ✅ Completed Optimizations

### 1. Batch Bar Fetching (`get_next_n_bars()`)
- **Added**: `get_next_n_bars()` method to `CachedDataFeed` for efficient batch fetching
- **Benefit**: Reduces function call overhead by fetching up to 10 bars at once
- **Location**: `core/live/data_feed_cached.py`

### 2. Optimized Logging Frequency
- **Changed**: Log every 100 bars instead of every bar
- **Benefit**: Reduces I/O overhead significantly (10x less logging)
- **Location**: `core/live/scheduler.py` - `_run_loop()` method

### 3. Replay Speed Control
- **API**: Already implemented in `LiveStartRequest` (accepts `replay_speed: float`)
- **UI**: Dropdown with options: 1x, 10x, 50x, 100x, 600x
- **Location**: 
  - API: `ui/fastapi_app.py`
  - UI: `ui/dashboard_modern.html`
  - Scheduler: `core/live/scheduler.py` (uses `replay_speed_multiplier`)

### 4. Mode Detection Fix
- **Fixed**: `get_live_status()` now correctly detects offline mode
- **Location**: `ui/bot_manager.py`
- **Result**: Status now shows `"mode": "offline"` when in cached/offline mode

### 5. Enhanced Logging
- **Added**: Clear OFFLINE MODE messages at startup
- **Added**: Replay speed and batch processing info in logs
- **Location**: `core/live/scheduler.py` - `_run_loop()` method

## 🧪 Validation Checklist

### Check 1: Start Simulation
```bash
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["SPY"],
    "broker_type": "cached",
    "offline_mode": true,
    "start_date": "2024-10-15",
    "fixed_investment_amount": 5000,
    "replay_speed": 600.0
  }'
```

**Expected Log Output:**
```
🔵 [LiveLoop] OFFLINE MODE ENABLED
🔵 [LiveLoop] Replay speed: 600.0x (0.100s per bar)
🔵 [LiveLoop] Processing up to 10 bars per iteration
🔵 [LiveLoop] Beginning replay at 2024-10-15 13:30:00+00:00
🔵 [LiveLoop] SPY processed 100 bars so far
🔵 [LiveLoop] SPY processed 200 bars so far
...
```

### Check 2: Status After 2 Seconds
```bash
curl http://localhost:8000/live/status
```

**Expected Response:**
```json
{
  "mode": "offline",
  "is_running": true,
  "bars_per_symbol": {
    "SPY": 180
  },
  "bar_count": 180,
  ...
}
```

### Check 3: Stop Simulation
```bash
curl -X POST http://localhost:8000/live/stop
```

**Expected Log Output:**
```
[LiveLoop] Stop requested
[LiveLoop] Finalizing...
[LiveLoop] Processed N bars total
[LiveLoop] Summary:
  SPY processed: XXXX bars
  Final equity: $....
```

## 🚀 Performance Improvements

### Before Optimizations:
- **Speed**: ~0.1 bars/second (1 bar every 10 seconds)
- **Logging**: Every bar logged (high I/O overhead)
- **Fetching**: Single bar per call (high function call overhead)

### After Optimizations:
- **Speed**: 50-80+ bars/second (target)
- **Logging**: Every 100 bars (10x reduction in I/O)
- **Fetching**: Batch of 10 bars per call (10x reduction in function calls)

## 📊 Replay Speed Options

| Speed | Sleep Interval | Use Case |
|-------|---------------|----------|
| 1x    | 60s per bar   | Real-time simulation |
| 10x   | 6s per bar    | Slow replay for debugging |
| 50x   | 1.2s per bar  | Medium speed |
| 100x  | 0.6s per bar  | Fast replay |
| 600x  | 0.1s per bar  | Maximum speed (default) |

## 🔍 Healthy Replay Engine Log Signature

A working offline replay should produce logs like this:

```
🔵 [LiveLoop] OFFLINE MODE ENABLED
🔵 [LiveLoop] Replay speed: 600.0x (0.100s per bar)
🔵 [LiveLoop] Processing up to 10 bars per iteration
🔵 [LiveLoop] Beginning replay at 2024-10-15 13:30:00+00:00
🔵 [LiveLoop] SPY processed 100 bars so far
🔵 [LiveLoop] SPY processed 200 bars so far
🔵 [LiveLoop] SPY processed 300 bars so far
...
✅ [LiveLoop] Finished all 500 cached bars for SPY
✅ [LiveLoop] Simulation complete - stopped due to end of data
[LiveLoop] Summary:
  SPY processed: 500 bars
  Final equity: $10422.19
```

## ⚠️ Known Issues & Fixes

### Issue: `bars_per_symbol` showing 0
- **Status**: Fixed in code, but may need restart to take effect
- **Cause**: Initialization timing or race condition
- **Fix**: Ensure `bars_per_symbol` is initialized before loop starts

### Issue: Mode showing "live" instead of "offline"
- **Status**: ✅ Fixed
- **Fix**: Updated `get_live_status()` to check `config.offline_mode` and `data_feed.cache_path`

## 🎯 Next Steps

1. **Validate batch fetching**: Confirm `get_next_n_bars()` is being called
2. **Monitor performance**: Check actual bars/second in logs
3. **Test multi-symbol**: Verify both SPY and QQQ process correctly
4. **Test different speeds**: Verify 1x, 10x, 50x, 100x, 600x all work
5. **Test clean stop**: Verify simulation stops gracefully

## 📝 Code Changes Summary

### Files Modified:
1. `core/live/data_feed_cached.py` - Added `get_next_n_bars()` method
2. `core/live/scheduler.py` - Updated `_run_loop()` to use batch fetching and optimized logging
3. `ui/bot_manager.py` - Fixed mode detection in `get_live_status()`
4. `ui/dashboard_modern.html` - Added 50x option to replay speed dropdown

### Key Methods:
- `CachedDataFeed.get_next_n_bars()` - Batch fetch bars
- `LiveTradingLoop._run_loop()` - Optimized bar processing loop
- `BotManager.get_live_status()` - Fixed mode detection

