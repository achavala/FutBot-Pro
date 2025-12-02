# Quick Start Guide - Gamma-Only Mode

## ✅ Fixed: Scripts Now Run in Background

All scripts have been updated to run the server in the background, so Cursor won't get stuck.

## 🚀 Quick Start (3 Commands)

### Terminal 1: Start Server
```bash
./START_GAMMA_ONLY.sh
```

**What it does:**
- Kills old processes
- Frees port 8000
- Sets `GAMMA_ONLY_TEST_MODE=true`
- Starts server in background
- Returns immediately (won't block Cursor)

**Expected output:**
```
✅ Server started successfully (PID: xxxxx)
📍 Dashboard: http://localhost:8000/dashboard
📜 Logs: tail -f logs/gamma_only_server.log
```

### Terminal 2: Verify Gamma-Only Mode
```bash
./VERIFY_GAMMA_MODE.sh
```

**Or check logs:**
```bash
tail -f logs/gamma_only_server.log | grep -i "GAMMA_ONLY\|Gamma Scalper only"
```

**Expected:**
- ✅ Found: GAMMA_ONLY_TEST_MODE=true
- ✅ Found: Gamma Scalper only agents created

### Terminal 3: Start Trading Loop

**Option A: Dashboard**
- Open: http://localhost:8000/dashboard
- Click "Start Live" or "Simulate"

**Option B: API**
```bash
./START_TRADING_LOOP.sh
```

## 📊 Monitor Activity

**Check Gamma Scalper activity:**
```bash
./CHECK_GAMMA_ACTIVITY.sh
```

**Watch logs:**
```bash
tail -f logs/gamma_only_server.log | grep -i "gamma\|deltahedge\|multileg"
```

**Expected log entries:**
- `[GAMMA SCALP] NEGATIVE GEX (...) → BUY Xx 25Δ strangle`
- `[MultiLeg] STRANGLE position created: ...`
- `[DeltaHedge] Hedging SELL X shares @ $Y`

## 🛑 Stop Server

```bash
./STOP_SERVER.sh
```

## 🔍 Troubleshooting

### Server Not Starting
```bash
# Check logs
tail -50 logs/gamma_only_server.log

# Check if port is in use
lsof -i :8000

# Kill everything
pkill -f "python.*main.py"
```

### Gamma Scalper Not Firing
**Check conditions:**
```bash
curl http://localhost:8000/microstructure
curl http://localhost:8000/options/iv?symbol=SPY
```

**Gamma Scalper needs:**
- ✅ `gex_regime == NEGATIVE`
- ✅ `gex_strength > 2.0` (billions)
- ✅ `iv_percentile < 30` (cheap IV)

**If conditions not met:** This is correct behavior - Gamma Scalper waits for favorable conditions.

## 📝 Helper Scripts

- `START_GAMMA_ONLY.sh` - Start server in background (recommended)
- `CLEAN_START_GAMMA_ONLY.sh` - Clean start with verification
- `STOP_SERVER.sh` - Stop server cleanly
- `VERIFY_GAMMA_MODE.sh` - Verify Gamma-only mode
- `START_TRADING_LOOP.sh` - Start trading via API
- `CHECK_GAMMA_ACTIVITY.sh` - Check Gamma Scalper activity

## 🎯 Success Checklist

- ✅ Server running (PID exists)
- ✅ Port 8000 responding
- ✅ Logs show `GAMMA_ONLY_TEST_MODE=true`
- ✅ Logs show "Gamma Scalper only agents"
- ✅ Trading loop started (`is_running: true`)
- ✅ Gamma Scalper positions created
- ✅ Delta hedging activity observed

## 💡 Pro Tips

1. **Use separate terminals** for server, monitoring, and commands
2. **Server runs in background** - scripts return immediately
3. **Check logs** if something seems wrong
4. **Wait for conditions** - Gamma Scalper is selective
5. **Use dashboard** for visual monitoring

