# 🚀 FutBot Pro - Market Open Launch Checklist

**Date:** Today  
**Market Open:** 9:30 AM ET  
**Status:** ✅ **APPROVED FOR LAUNCH**

---

## ✅ **FINAL APPROVAL CONFIRMED**

### **System Status: PRODUCTION-READY**

- ✅ All safety guards active
- ✅ Real Alpaca paper orders configured
- ✅ SIM-only mode for unsupported operations
- ✅ All validations passing
- ✅ No blocking issues

---

## 📋 **PRE-MARKET CHECKLIST (Run at 9:29 AM ET)**

### **Step 1: Set Environment Variables**

```bash
export ALPACA_API_KEY="your_paper_api_key"
export ALPACA_SECRET_KEY="your_paper_secret_key"
export ALPACA_BASE_URL="https://paper-api.alpaca.markets"
```

**Verify:**
```bash
echo $ALPACA_API_KEY  # Should show your key
echo $ALPACA_BASE_URL  # Should show paper-api.alpaca.markets
```

---

### **Step 2: Run Validation Script**

```bash
cd /Users/chavala/FutBot
source .venv/bin/activate
python scripts/validate_alpaca_options_paper.py
```

**Expected Output:**
```
✅ ALL VALIDATIONS PASSED
🎯 READY FOR PAPER TRADING
```

**If any checks fail:** Do NOT proceed. Fix issues first.

---

### **Step 3: Verify Server is Running**

```bash
curl http://localhost:8000/health
```

**Expected:** `{"status":"ok"}`

**If not running:**
```bash
python main.py --mode api --port 8000
```

---

### **Step 4: Check Account Status**

```bash
curl http://localhost:8000/status
```

**Verify:**
- `is_running: false` (not already running)
- No error messages

---

## 🚀 **LAUNCH COMMAND (Run at 9:30 AM ET)**

```bash
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["SPY", "QQQ"],
    "broker_type": "alpaca",
    "offline_mode": false,
    "testing_mode": false,
    "strict_data_mode": false,
    "replay_speed": 1.0,
    "fixed_investment_amount": 10000
  }'
```

**Expected Response:**
```json
{
  "status": "started",
  "message": "Live trading started"
}
```

---

## 🔍 **MONITORING - What to Watch For**

### **1. Real Order Logs (Buying Strategies)**

**OptionsAgent (Buying Calls/Puts):**
```
📤 [REAL ORDER] Submitting BUY 2 contracts of QQQ241206C00493000 @ $3.45
✅ [REAL ORDER] Order submitted: abc123, Status: filled, Filled: 2/2 @ $3.45
```

**GammaScalperAgent (Buying Strangles):**
```
[GAMMA SCALP] NEGATIVE GEX (3.2B) + IV=19.3% → BUY 5x 25Δ strangle
📤 [REAL ORDER] Submitting BUY 5 contracts of SPY241206P00450 @ $2.10
📤 [REAL ORDER] Submitting BUY 5 contracts of SPY241206C00475 @ $1.98
✅ [REAL ORDER] Order submitted: xyz789, Status: filled
```

### **2. SIM-Only Logs (Selling Strategies)**

**ThetaHarvesterAgent (Selling Straddles):**
```
[THETA HARVEST] Compression + IV=78.5% → SELL 4x ATM straddle (SIM MODE - Alpaca paper limitation)
⚠️ [SIM ONLY] Skipping real order for SPY_STRADDLE - marked as simulation-only
```

**This is CORRECT behavior** - Alpaca paper doesn't support naked selling.

---

## 📊 **DASHBOARD MONITORING**

### **Check These Endpoints:**

1. **Live Status:**
   ```bash
   curl http://localhost:8000/live/status
   ```
   - `is_running: true`
   - `bars_per_symbol` increasing
   - `last_bar_time` updating

2. **Trade History:**
   ```bash
   curl http://localhost:8000/trades/roundtrips
   ```
   - Real trades appearing
   - Prices matching market

3. **Options Trades:**
   ```bash
   curl http://localhost:8000/trades/options/roundtrips
   ```
   - Options positions tracked

4. **Alpaca Dashboard:**
   - https://app.alpaca.markets/paper/trade
   - Verify orders are appearing
   - Check positions

---

## ⚠️ **IMPORTANT REMINDERS**

### **1. Market Hours**
- Alpaca options orders only fill **9:30 AM - 4:00 PM ET**
- Orders placed outside hours will sit in "accepted" state
- This is normal Alpaca behavior

### **2. Straddle Selling**
- ThetaHarvesterAgent uses **SIM mode only**
- This prevents Alpaca rejections
- Strategy still runs and tracked
- No errors expected

### **3. Order Types**
- System uses **LIMIT orders** when price available (safer)
- Falls back to **MARKET orders** if needed
- All orders logged with `[REAL ORDER]` tag

### **4. Position Tracking**
- Real positions tracked in Alpaca
- SIM positions tracked in local portfolio
- Both visible in dashboard

---

## 🛑 **EMERGENCY STOP**

If you need to stop trading immediately:

```bash
curl -X POST http://localhost:8000/live/stop
```

Or:
```bash
# Kill the process
pkill -f "python.*main.py"
```

---

## ✅ **SUCCESS CRITERIA**

After 30 minutes of trading, you should see:

1. ✅ Real orders in Alpaca dashboard
2. ✅ `[REAL ORDER]` messages in logs
3. ✅ Positions appearing in `/trades/roundtrips`
4. ✅ No error messages
5. ✅ GEX calculations updating
6. ✅ IV percentile calculations working

---

## 📞 **TROUBLESHOOTING**

### **No Real Orders Appearing**

**Check:**
1. Are you using Alpaca broker? (`broker_type: "alpaca"`)
2. Are credentials set? (`echo $ALPACA_API_KEY`)
3. Is market open? (9:30 AM - 4:00 PM ET)
4. Are agents generating signals? (check logs)

### **Orders Rejected**

**Check:**
1. Is it a SELL order? (Should be SIM-only)
2. Is buying power sufficient?
3. Check Alpaca dashboard for rejection reason

### **No Options Trades**

**Check:**
1. Is OptionsAgent enabled?
2. Are options signals being generated?
3. Check logs for `[OptionsAgent]` messages
4. Verify options data feed is working

---

## 🎯 **FINAL CONFIRMATION**

Before launching, confirm:

- [ ] Environment variables set
- [ ] Validation script passed
- [ ] Server is running
- [ ] Market is open (9:30 AM ET)
- [ ] Alpaca dashboard accessible
- [ ] Ready to monitor logs

**If all checked:** ✅ **YOU ARE READY TO LAUNCH**

---

## 🚀 **LAUNCH COMMAND (Copy/Paste Ready)**

```bash
# Set credentials (if not already set)
export ALPACA_API_KEY="your_key"
export ALPACA_SECRET_KEY="your_secret"
export ALPACA_BASE_URL="https://paper-api.alpaca.markets"

# Validate
python scripts/validate_alpaca_options_paper.py

# Launch (at 9:30 AM ET)
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["SPY", "QQQ"],
    "broker_type": "alpaca",
    "offline_mode": false,
    "testing_mode": false,
    "strict_data_mode": false,
    "replay_speed": 1.0,
    "fixed_investment_amount": 10000
  }'
```

---

**Status:** ✅ **APPROVED - READY FOR MARKET OPEN**

**Good luck! 🚀**


