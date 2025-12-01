# 🚀 Auto-Start Live Trading Guide

## Overview

Your FutBot system is **healthy and ready**, but it needs **live market data** to start trading. This guide explains how to automatically start trading when market data becomes available.

---

## 🔍 Why No Trades Yet?

### **The System is Waiting for Live Bars**

Your dashboard shows:
- ✅ System is healthy
- ✅ All components loaded
- ✅ API responding quickly (72ms)
- ❌ **"Waiting for Data — No bars collected yet"**

### **Why?**

**Alpaca Paper Trading provides:**
- ❌ **No real-time data** (15-minute delay)
- ❌ **No data before market opens**
- ✅ **Delayed bars after 9:30 AM EST** (first bar arrives at ~9:45 AM EST)

**Your system is correctly waiting for the first delayed candle.**

---

## 🕒 When Will Data Arrive?

| Time (EST) | What Happens |
|------------|--------------|
| **9:30 AM** | Market opens |
| **9:45 AM** | First delayed bar arrives (9:30 AM candle) |
| **9:46 AM+** | Bars continue every 15 minutes |

**Your bot will automatically start when the first bar arrives.**

---

## ✅ Solution 1: Dashboard Auto-Start (Recommended)

The dashboard **automatically detects live bars** and starts trading:

### **How It Works:**
1. Dashboard checks market status every 30 seconds
2. When market opens, it checks for live bars
3. When live bars are detected (from today, within last hour), it auto-starts
4. No manual intervention needed!

### **What You See:**
- Dashboard shows "Waiting for live bars..." when market is open but no bars yet
- Toast notification: "Auto-trading started: SPY & QQQ (Live Mode)" when started
- Status changes from "System Stopped" to "System Running"

### **Just Keep the Dashboard Open**
The dashboard will handle everything automatically.

---

## ✅ Solution 2: Standalone Auto-Start Script

For more control, use the standalone script:

### **Start the Script Before Market Opens:**

```bash
cd /Users/chavala/FutBot
python scripts/auto_start_live.py
```

### **What It Does:**
- Polls API every 30 seconds
- Checks for live bars (from today, recent)
- Automatically starts live trading when bars are detected
- Logs all activity for monitoring

### **Output Example:**

```
============================================================
AUTO-START LIVE TRADING - Waiting for Market Data
============================================================
API Base: http://localhost:8000
Poll Interval: 30 seconds

Market Status: CLOSED
Live Trading: STOPPED
Mode: backtest

Waiting for live market bars to start flowing...
(Alpaca Paper provides 15-min delayed data after market opens)

[09:30:00] No live bars yet - waiting...
[09:30:30] No live bars yet - waiting...
[09:45:00] ✅ Live bars detected: 2025-12-01T09:30:00 (age: 15.0 min)
✅ Live bars detected (1/2)
✅ Live bars detected (2/2)

🎯 Live data confirmed - Starting trading session!

🚀 Attempting to start live trading...
✅ Live trading started successfully!

============================================================
✅ AUTO-START COMPLETE
============================================================
Live trading is now active.
Monitor the dashboard for trade activity.
```

---

## 🎯 What Happens After Auto-Start?

Once live bars start flowing and trading begins:

### **Dashboard Updates:**
- ✅ Status: "System Running"
- ✅ Bars per symbol updating
- ✅ Regime classification active
- ✅ Agents evaluating trades
- ✅ GEX updates every 5 minutes

### **Trading Activity:**
- **Directional Options Agent**: Buying calls/puts based on regime + GEX
- **Gamma Scalper Agent**: Buying strangles on negative GEX + cheap IV
- **Theta Harvester Agent**: Selling straddles (SIM-ONLY in Alpaca paper)

### **Real Orders:**
- Single-leg options: **Real Alpaca paper orders**
- Multi-leg options: **SIM-ONLY** (Alpaca paper limitation)

---

## 🔧 Manual Start (If Needed)

If auto-start doesn't work, manually start:

### **Via Dashboard:**
1. Click "► Start Live" button
2. Wait for confirmation toast

### **Via API:**
```bash
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["SPY", "QQQ"],
    "broker_type": "alpaca",
    "offline_mode": false,
    "testing_mode": true,
    "fixed_investment_amount": 10000.0
  }'
```

---

## 📊 Monitoring

### **Check Status:**
```bash
# Live trading status
curl http://localhost:8000/live/status | python3 -m json.tool

# Health check
curl http://localhost:8000/health | python3 -m json.tool

# Current regime
curl http://localhost:8000/regime | python3 -m json.tool
```

### **Watch Logs:**
```bash
# If running via uvicorn
tail -f logs/api_server.log

# If running via script
# Logs appear in terminal
```

---

## ⚠️ Troubleshooting

### **"No live bars yet" for a long time:**
- ✅ Check market is actually open (9:30 AM - 4:00 PM EST)
- ✅ Verify Alpaca credentials in `.env`
- ✅ Check Alpaca paper account is active
- ✅ Wait for 9:45 AM EST (first delayed bar)

### **Auto-start not triggering:**
- ✅ Check browser console for errors (F12)
- ✅ Verify API server is running
- ✅ Check `/live/status` endpoint returns data
- ✅ Use standalone script as backup

### **"System Stopped" after auto-start:**
- ✅ Check API logs for errors
- ✅ Verify broker connection
- ✅ Check risk manager status
- ✅ Review `/health` endpoint for errors

---

## 🎉 Summary

**Your system is ready!** Just:

1. **Keep dashboard open** (auto-starts automatically)
   OR
2. **Run `python scripts/auto_start_live.py`** before market opens

**The bot will start trading automatically when Alpaca delivers the first delayed bar (~9:45 AM EST).**

No manual intervention needed! 🚀

