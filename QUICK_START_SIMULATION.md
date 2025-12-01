# Quick Start: Simulation with testing_mode: true

## 🎯 Fastest Method (30 seconds)

### Step 1: Open Dashboard
```
http://localhost:8000/dashboard
```

### Step 2: Select Date/Time
- **Start:** Click "Start Date/Time" → Choose "Wed, Nov 26, 2025 9:30 A"
- **End:** Click "End Date/Time" → Choose "Wed, Nov 26, 2025 1:00 P"

### Step 3: Click "Start" Button
- Green button in the header (next to the date/time dropdowns)
- Or look for the "Simulate" button

### Step 4: Done! ✅
- `testing_mode: true` is automatically included
- Simulation starts immediately
- Check Status tab to see progress

---

## 🔍 Verify It's Working

### Check Status (Terminal)
```bash
curl -s http://localhost:8000/live/status | python3 -m json.tool
```

**Expected:**
```json
{
  "is_running": true,
  "mode": "offline",
  "bars_per_symbol": {
    "SPY": 100,    // Should increase
    "QQQ": 100     // Should increase
  }
}
```

### Check Logs (Dashboard)
1. Go to **Settings** tab
2. Open **Log Viewer**
3. Filter by: **INFO** and **Controller**
4. Look for:
   - `"Agent X generated Y intents"`
   - `"After filtering: X intents remain"`
   - `"Final intent: delta=..."`
   - `"[TradeExecution] Executing trade"`

### Check Trades
- **Dashboard** → **Trades** tab
- Or terminal: `curl -s http://localhost:8000/trade-log | python3 -m json.tool`

---

## 🚨 If Simulation Doesn't Start

### 1. Stop Previous Simulation
```bash
curl -X POST http://localhost:8000/live/stop
```

### 2. Check Server Status
```bash
curl http://localhost:8000/health
```

### 3. Check Logs
```bash
tail -f /tmp/futbot_server.log
```

---

## 📋 Alternative: API Method

If dashboard doesn't work, use API directly:

```bash
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["SPY", "QQQ"],
    "broker_type": "cached",
    "offline_mode": true,
    "testing_mode": true,
    "replay_speed": 600.0,
    "start_time": "2025-11-26T09:30:00",
    "end_time": "2025-11-26T16:00:00",
    "fixed_investment_amount": 10000.0
  }'
```

---

## ✅ Success Indicators

You'll know it's working when you see:

1. ✅ Status shows `"is_running": true`
2. ✅ `bars_per_symbol` increases (starts at 100, then grows)
3. ✅ Logs show agent evaluation
4. ✅ Logs show trade execution (if signals are generated)
5. ✅ Trades appear in Dashboard → Trades tab

---

## 🎯 What testing_mode: true Does

- ✅ Allows trading with minimal bars (1 bar minimum)
- ✅ Bypasses strict confidence filters
- ✅ Bypasses regime restrictions
- ✅ Bypasses volatility restrictions
- ✅ Forces aggressive trading for testing

This ensures trades execute even in testing scenarios!

