# Clean Start Guide - Gamma-Only Mode

## ✅ Current Status

- ✅ All processes cleaned up
- ✅ Port 8000 is free
- ✅ Helper scripts created
- ⏳ Ready for clean start

## 🚀 Quick Start Sequence

### Step 1: Start Server with Gamma-Only Mode

```bash
./CLEAN_START_GAMMA_ONLY.sh
```

**Or manually:**
```bash
export GAMMA_ONLY_TEST_MODE=true
export FUTBOT_LOG_LEVEL=INFO
python3 main.py --mode api --port 8000
```

**Watch for these startup messages:**
- `🔬 GAMMA_ONLY_TEST_MODE=true (env var: true)`
- `🔬 GAMMA_ONLY_TEST_MODE enabled - creating Gamma Scalper only agents`
- `✅ Created X agents (Gamma Scalper only)`

### Step 2: Verify Gamma-Only Mode is Active

**In a new terminal:**
```bash
./VERIFY_GAMMA_MODE.sh
```

**Or check logs manually:**
```bash
tail -f logs/*.log | grep -i "GAMMA_ONLY\|Gamma Scalper only"
```

**Expected output:**
- ✅ Found: GAMMA_ONLY_TEST_MODE=true
- ✅ Found: Gamma Scalper only agents created
- ✅ Found: Created X agents

### Step 3: Start Trading Loop

**Option A: Dashboard (Recommended)**
1. Open: http://localhost:8000/dashboard
2. Click "Start Live" or "Simulate"
3. Make sure `offline_mode=true` is set

**Option B: API**
```bash
./START_TRADING_LOOP.sh
```

**Or manually:**
```bash
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["SPY"], "offline_mode": true}'
```

### Step 4: Monitor Gamma Scalper Activity

**Check activity:**
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

## 🔍 Troubleshooting

### If Gamma Scalper Doesn't Fire

**Check GEX conditions:**
```bash
curl http://localhost:8000/microstructure
```

**Check IV conditions:**
```bash
curl http://localhost:8000/options/iv?symbol=SPY
```

**Gamma Scalper fires ONLY when:**
- ✅ `gex_regime == NEGATIVE`
- ✅ `gex_strength > 2.0` (billions)
- ✅ `iv_percentile < 30` (cheap IV)

**If conditions not met:**
- This is **correct behavior**, not a bug
- Gamma Scalper waits for favorable conditions
- May take time for conditions to align

### If Server Won't Start

**Check port:**
```bash
lsof -i :8000
```

**Kill any remaining processes:**
```bash
pkill -f "python.*main.py"
pkill -f "uvicorn"
```

**Force cleanup:**
```bash
killall -9 python
```

### If Trading Loop Won't Start

**Check server health:**
```bash
curl http://localhost:8000/health
```

**Check if already running:**
```bash
curl -s http://localhost:8000/health | python3 -m json.tool | grep is_running
```

## 📊 Success Indicators

### Server Started Correctly
- ✅ Port 8000 responding
- ✅ Health endpoint returns `"status": "healthy"`
- ✅ Logs show `GAMMA_ONLY_TEST_MODE=true`
- ✅ Logs show "Gamma Scalper only agents"

### Trading Loop Started
- ✅ `is_running: true` in health check
- ✅ `bar_count` increasing
- ✅ Logs show bar processing

### Gamma Scalper Active
- ✅ Logs show `[GAMMA SCALP]` entries
- ✅ Multi-leg positions created
- ✅ Delta hedging activity
- ✅ Positions visible in dashboard

## 🎯 Next Steps After Gamma Packages Complete

**After 1-2 complete Gamma packages (entry → exit):**

1. **Export timelines:**
```bash
./EXPORT_TIMELINES.sh
```

2. **Or via API:**
```bash
curl -X POST http://localhost:8000/options/export-timelines
```

3. **Check exported files:**
```bash
ls -la phase1_results/gamma_only/*/
```

## 📝 Helper Scripts Created

- `CLEAN_START_GAMMA_ONLY.sh` - Clean start with Gamma-only mode
- `VERIFY_GAMMA_MODE.sh` - Verify Gamma-only mode is active
- `START_TRADING_LOOP.sh` - Start trading loop via API
- `CHECK_GAMMA_ACTIVITY.sh` - Check for Gamma Scalper activity
- `MONITOR_GAMMA_TEST.sh` - General monitoring

## 🚨 Common Issues Fixed

1. ✅ **Multiple processes** - Cleaned up
2. ✅ **Port conflicts** - Port 8000 freed
3. ✅ **Gamma-only mode not set** - Script sets env var
4. ✅ **Split state** - Single process controls UI + scheduler

## 💡 Pro Tips

- **Always use `offline_mode=true`** for testing
- **Monitor logs in real-time** to catch issues early
- **Check GEX/IV conditions** if Gamma doesn't fire
- **Wait for conditions** - Gamma Scalper is selective
- **Use dashboard** for visual monitoring

