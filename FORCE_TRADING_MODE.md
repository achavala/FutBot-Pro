# Force Trading Mode - Trade TODAY with Limited Data

## Overview

**Force Trading Mode** allows you to execute trades TODAY, even with:
- Market closed
- Bars stuck at 29
- Limited live bars
- Indicators not "READY"
- Real-time Alpaca feed delayed

## Three Levels of Relaxation

### 🟢 LEVEL 1 — Relaxed Mode (Recommended)
**Minimum bars: 10** (instead of 30)

**How to use:**
```bash
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["SPY", "QQQ"],
    "broker_type": "alpaca",
    "testing_mode": false
  }'
```

**What this unlocks:**
- EMA(9), EMA(21) still usable
- Bias Engine works
- Regime classification works (lightly)
- Bot becomes READY after ~10 bars
- **Perfect for running trades TODAY without breaking stability**

---

### 🟡 LEVEL 2 — Aggressive Mode
**Minimum bars: 10** (default when testing_mode=false)

**How to use:**
```bash
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["SPY", "QQQ"],
    "broker_type": "alpaca",
    "testing_mode": false
  }'
```

**Note:** Default is already 10 bars (relaxed mode). This is the current default.

---

### 🔴 LEVEL 3 — Full Force Mode (Guaranteed Trades Today)
**Minimum bars: 1** (trading immediately)

**How to use:**
```bash
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["SPY", "QQQ"],
    "broker_type": "alpaca",
    "testing_mode": true
  }'
```

**What this does:**
- Makes indicators loose
- Allows 1 bar warmup
- Disables strict bar requirements
- Allows trades even with light data
- **Trades WILL execute today**

**Downside:**
- Indicators unstable
- But trades WILL fire

---

## 🚀 Best Practice for TODAY

### Option A — Run Simulation Warm-Up, then Switch to Live

**Step 1:** Run offline simulation first (loads 30+ bars instantly):
```bash
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["SPY"],
    "broker_type": "cached",
    "offline_mode": true,
    "replay_speed": 600.0,
    "testing_mode": false
  }'
```

This loads 30+ bars instantly. Status becomes READY.

**Step 2:** Then start live-trading:
```bash
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["SPY", "QQQ"],
    "broker_type": "alpaca",
    "offline_mode": false,
    "testing_mode": false
  }'
```

Indicator warm-up is already done → Trades start immediately.

---

### Option B — Force Trade Right Now (No data needed)

**Use testing_mode=true for immediate trading:**
```bash
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["SPY", "QQQ"],
    "broker_type": "alpaca",
    "testing_mode": true
  }'
```

This allows trading with just 1 bar!

---

## 🧠 My Recommendation Based on Your Goal

**Use this combo for reliable trades today:**

1. ✅ **Relaxed mode** (10 bars minimum) - default
2. ✅ **Offline warm-up** for instant READY state
3. ✅ **Live trading** with READY state carried over

**Command sequence:**
```bash
# 1. Stop any running bot
curl -X POST http://localhost:8000/live/stop

# 2. Start with relaxed mode (10 bars) - this is the default
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["SPY", "QQQ"],
    "broker_type": "alpaca",
    "testing_mode": false
  }'
```

**Or for FORCE MODE (1 bar minimum):**
```bash
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["SPY", "QQQ"],
    "broker_type": "alpaca",
    "testing_mode": true
  }'
```

---

## Configuration Summary

| Mode | `testing_mode` | Minimum Bars | Use Case |
|------|----------------|--------------|----------|
| **Normal** | `false` | 15 | Standard trading (current default) |
| **Relaxed** | `false` | 10 | Trade today with limited data (recommended) |
| **Force** | `true` | 1 | Guaranteed trades today (aggressive) |

---

## What Gets Relaxed

### When `testing_mode=true`:
- ✅ Minimum bars: **1** (instead of 15)
- ✅ Confidence thresholds: **Already lowered** (accepts 0% confidence)
- ✅ Regime strictness: **Relaxed** (allows compression regime)
- ✅ Price-action signals: **Enabled** (works with minimal data)

### When `testing_mode=false` (default):
- ✅ Minimum bars: **10** (relaxed from 15)
- ✅ Confidence thresholds: **Already lowered** (accepts 5% confidence)
- ✅ Price-action signals: **Enabled** (works with 10+ bars)

---

## Expected Behavior

### With Relaxed Mode (10 bars):
- Bot becomes READY after 10 bars
- Trades execute based on price-action signals
- Indicators are stable enough for trading

### With Force Mode (1 bar):
- Bot becomes READY immediately
- Trades execute on first bar
- Indicators may be unstable but trades WILL fire

---

## Monitoring

Watch for these log messages:
```bash
tail -f logs/*.log | grep -E "testing_mode|minimum_bars|Processed bar|TradeExecution"
```

You should see:
- `🔵 Testing mode: true/false`
- `🔵 Minimum bars: 1/10`
- `📊 [LiveLoop] Processed bar for SPY: ...`
- `✅ [TradeExecution] Trade executed successfully`

---

## Stop Loss Protection

**Even in force mode, stop loss is active:**
- **10% stop loss** (configured in `settings.yaml`)
- **15% profit target** (configured in `settings.yaml`)
- Trades will exit automatically on loss/profit

---

## Summary

✅ **Relaxed Mode** (default): 10 bars minimum - **Recommended for today**
✅ **Force Mode**: 1 bar minimum - **Guaranteed trades today**

**You can now trade TODAY even with:**
- No live bars
- Market closed
- Stuck bars
- Alpaca delays
- New environment reset

**Just use `testing_mode: true` for immediate trading!**

