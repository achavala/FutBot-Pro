# Alpaca Options Paper Trading - Safety Guide

## ✅ System Status: READY FOR MARKET OPEN

Your system is configured for **safe Alpaca options paper trading** with automatic protection against unsupported operations.

---

## 🛡️ Safety Features Implemented

### 1. **Automatic Alpaca Paper Mode Detection**
- ThetaHarvesterAgent automatically detects when using Alpaca paper trading
- Straddle selling is automatically disabled (SIM mode only)
- No configuration needed - works automatically

### 2. **SIM-Only Flag System**
- Straddle trades are marked with `sim_only=True` in metadata
- Executor automatically skips real order submission for SIM-only trades
- Graceful fallback to synthetic execution

### 3. **Buying Strategies Work Normally**
- ✅ OptionsAgent (buying calls/puts): **REAL orders**
- ✅ GammaScalperAgent (buying strangles): **REAL orders**
- ⚠️ ThetaHarvesterAgent (selling straddles): **SIM mode only**

---

## 📋 What Works at Market Open (9:30 AM ET)

### ✅ **REAL Orders Will Be Placed:**
1. **Buying Options** (calls/puts)
   - OptionsAgent generates buy signals
   - Real Alpaca orders placed automatically
   - Logs: `📤 [REAL ORDER] Submitting BUY ...`

2. **Buying Strangles**
   - GammaScalperAgent generates buy signals
   - Real Alpaca orders placed automatically
   - Logs: `📤 [REAL ORDER] Submitting BUY ...`

### ⚠️ **SIM Mode Only (No Real Orders):**
1. **Selling Straddles**
   - ThetaHarvesterAgent generates sell signals
   - Marked as SIM-only (no real orders)
   - Logs: `[THETA HARVEST] ... (SIM MODE - Alpaca paper limitation)`
   - Logs: `⚠️ [SIM ONLY] Skipping real order ...`

---

## 🚨 Important Alpaca Limitations

### 1. **Market Hours Only**
- Alpaca options orders only fill during **9:30 AM - 4:00 PM ET**
- Orders placed outside market hours will sit in "accepted" state
- This is normal Alpaca behavior

### 2. **Naked Options Selling Not Supported**
- Alpaca paper accounts **do not allow selling naked options**
- Requires Level 3 options approval (not available in paper)
- Would result in: `422 Unprocessable entity: insufficient buying power`
- **Solution:** System automatically uses SIM mode for straddle selling

---

## 🎯 Pre-Market Checklist

Before market opens at 9:30 AM ET:

```bash
# 1. Set credentials
export ALPACA_API_KEY="your_paper_api_key"
export ALPACA_SECRET_KEY="your_paper_secret_key"
export ALPACA_BASE_URL="https://paper-api.alpaca.markets"

# 2. Validate setup
python scripts/validate_alpaca_options_paper.py

# 3. Start bot (when market opens)
# Orders will be placed automatically!
```

---

## 📊 Monitoring Real Orders

### Log Messages to Watch For:

**Real Orders (Buying):**
```
📤 [REAL ORDER] Submitting BUY 2 contracts of SPY251126P00673000 @ $3.45
✅ [REAL ORDER] Order submitted: abc123, Status: filled, Filled: 2/2 @ $3.45
```

**SIM Mode (Selling Straddles):**
```
[THETA HARVEST] Compression + IV=78.5% → SELL 4x ATM straddle (SIM MODE - Alpaca paper limitation)
⚠️ [SIM ONLY] Skipping real order for SPY_STRADDLE - marked as simulation-only
```

### Alpaca Dashboard:
- Monitor orders: https://app.alpaca.markets/paper/trade
- Check positions: https://app.alpaca.markets/paper/positions

---

## ✅ Final Validation

Run this before market open:

```bash
python scripts/validate_alpaca_options_paper.py
```

Expected output:
```
✅ ALL VALIDATIONS PASSED
🎯 READY FOR PAPER TRADING
```

---

## 🎉 You're Ready!

Your system will:
- ✅ Place **real Alpaca paper orders** for buying strategies
- ✅ Use **SIM mode** for selling strategies (safe, no rejections)
- ✅ Log all activity clearly
- ✅ Track all trades (real + simulated)

**Safe to run at 9:30 AM ET today!** 🚀


