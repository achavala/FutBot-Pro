# Quick Fix: IBKR Connection Timeout

## The Problem

Port 4002 is open, but API connection times out. This means the **API socket server isn't enabled**.

## Quick Fix (2 minutes)

### Step 1: Check API Settings

In IB Gateway:
1. Go to: **Configure** → **API** → **Settings**
2. Look for this checkbox at the **top** of the settings:
   - ✅ **"Enable ActiveX and Socket Clients"**
   - OR
   - ✅ **"Enable Socket Clients"**
   - OR  
   - ✅ **"Enable API"**

3. **This checkbox MUST be checked** ✅

### Step 2: Restart IB Gateway

**Critical**: After checking the box:
1. Click **OK** to save
2. **Close IB Gateway completely** (quit the application)
3. **Reopen IB Gateway**
4. **Log back in**
5. Wait for it to fully connect (you'll see account updates)

### Step 3: Test Again

```bash
python scripts/diagnose_ibkr.py
```

You should see:
```
✅ Successfully connected on port 4002!
```

## If You Can't Find the Checkbox

Sometimes it's:
- On a different tab in API Settings
- Named slightly differently
- In **Configure** → **API** → **Precautions**

## Alternative: Use TWS Instead

If IB Gateway doesn't work:
1. Download TWS (full Trader Workstation)
2. Same API settings apply
3. Sometimes TWS works better for API connections

## Once Connected

Start FutBot:
```bash
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["QQQ"],
    "broker_type": "ibkr",
    "ibkr_host": "127.0.0.1",
    "ibkr_port": 4002,
    "ibkr_client_id": 3
  }'
```

---

# Preload Performance Improvements

## The Problem

IBKR's historical data API is slow, especially for 1-day requests. Preload was timing out and only loading 11 bars instead of 50+.

## Fixes Applied ✅

### 1. Faster Duration (Fixed)
- **Changed**: `"1 D"` → `"1 H"` (1 hour instead of 1 day)
- **Result**: Much faster API response (60 minutes vs 390 minutes of data)
- **Location**: `core/live/data_feed_ibkr.py`

### 2. Polygon Cache Fallback (New)
- **Added**: Tries Polygon cache first (if configured)
- **Result**: Instant preload if cache available
- **Fallback**: IBKR if cache insufficient
- **Location**: `core/live/data_feed_ibkr.py` `_try_load_from_cache()`

### 3. Increased Timeout (Fixed)
- **Changed**: 60s → 90s timeout
- **Result**: More time for slow IBKR responses
- **Location**: `core/live/data_feed_ibkr.py`

### 4. Graceful Partial Preload (Fixed)
- **Added**: Bot continues with partial bars
- **Result**: Starts trading once 50+ bars accumulated naturally
- **Location**: `core/live/scheduler.py`

## Expected Behavior

1. **Fast preload**: Cache loads instantly if available
2. **Faster IBKR**: 1-hour duration responds much faster
3. **Graceful degradation**: Bot starts with partial bars and accumulates naturally
4. **Better logging**: Clear messages about preload status

## Status

- ✅ Duration format fixed (`"1 H"` instead of `"1 D"`)
- ✅ Client ID auto-generation (prevents conflicts)
- ✅ Polygon cache integration (optional, faster)
- ✅ Increased timeout (90s)
- ✅ Partial preload handling (graceful degradation)

The bot will now:
- Load bars faster (cache first, then shorter IBKR duration)
- Handle partial preloads gracefully
- Start trading once it accumulates 50+ bars naturally
- Provide better visibility into preload status

**Note**: If you see warnings about partial preload (e.g., "Only 11 bars loaded"), the bot will continue running and accumulate bars over time. Trading will begin automatically once enough bars are available.

