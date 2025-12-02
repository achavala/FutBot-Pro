# Step 2: Gamma-Only Test Execution - Instructions

## Current Status

✅ **Server Running:** Port 8000, 15,327 bars processed  
❌ **Gamma-Only Mode:** NOT active (server started without env var)  
❌ **Gamma Scalper Activity:** None (normal agents running instead)

## Problem

The server was started **without** `GAMMA_ONLY_TEST_MODE=true`, so it's using normal agents (Theta Harvester + Gamma Scalper) instead of Gamma Scalper only.

## Solution: Restart Server with Gamma-Only Mode

### Option 1: Use Helper Script (Recommended)

```bash
./RESTART_GAMMA_ONLY.sh
```

This script will:
1. Find and stop the current server
2. Free up port 8000
3. Start server with `GAMMA_ONLY_TEST_MODE=true`

### Option 2: Manual Restart

**Step 1: Stop Current Server**
```bash
# Find the process
ps aux | grep "python.*main.py.*--mode api" | grep -v grep

# Kill it (replace <PID> with actual process ID)
kill <PID>

# Or force kill if needed
kill -9 <PID>
```

**Step 2: Verify Port is Free**
```bash
lsof -i :8000
# Should show nothing, or kill any remaining process
```

**Step 3: Start with Gamma-Only Mode**
```bash
GAMMA_ONLY_TEST_MODE=true ./START_VALIDATION.sh
```

## Verification

After restart, check logs for:

```
🔬 GAMMA_ONLY_TEST_MODE=true (env var: true)
🔬 GAMMA_ONLY_TEST_MODE enabled - creating Gamma Scalper only agents
✅ Created X agents (Gamma Scalper only)
```

**Check server status:**
```bash
curl -s http://localhost:8000/health | python3 -m json.tool | grep -E "is_running|status"
```

## Start Trading Loop

Once server is running with Gamma-only mode:

**Option A: Dashboard**
- Open: http://localhost:8000/dashboard
- Click "Start Live" or "Simulate"

**Option B: API**
```bash
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["SPY"], "offline_mode": true}'
```

## Monitor Gamma Scalper Activity

**Check for positions:**
```bash
./CHECK_GAMMA_ACTIVITY.sh
```

**Watch logs:**
```bash
tail -f logs/*.log | grep -i "gamma\|deltahedge\|multileg"
```

**Expected log entries:**
- `[GAMMA SCALP] NEGATIVE GEX (...) → BUY Xx 25Δ strangle`
- `[MultiLeg] STRANGLE position created: ...`
- `[DeltaHedge] Hedging SELL X shares @ $Y`
- `[DeltaHedge] Hedging BUY X shares @ $Y`

## Success Criteria

✅ Server restarted with `GAMMA_ONLY_TEST_MODE=true`  
✅ Logs show "Gamma Scalper only agents"  
✅ Trading loop started  
✅ At least 1-2 Gamma Scalper positions created  
✅ Delta hedging activity observed  
✅ 1-2 complete packages (entry → hedging → exit)

## Next Step

After 1-2 complete Gamma packages:
```bash
./EXPORT_TIMELINES.sh
```

Or:
```bash
curl -X POST http://localhost:8000/options/export-timelines
```

