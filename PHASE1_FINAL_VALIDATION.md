# Phase 1 Final Validation Guide

## 🎯 Purpose

This guide provides step-by-step validation to confirm Phase 1 is 100% complete and all improvements are working correctly.

---

## ✅ STEP 1: Verify Strict Data Mode Works

### Purpose
Ensure wrong prices can never be used again - system should use cached data or fail hard.

### Test Command
```bash
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["QQQ"],
    "broker_type": "cached",
    "offline_mode": true,
    "testing_mode": true,
    "replay_speed": 500.0,
    "start_time": "2025-11-26T09:30:00Z",
    "end_time": "2025-11-26T10:00:00Z",
    "fixed_investment_amount": 10000.0
  }'
```

### Validation
```bash
# Wait 5 seconds for simulation to complete
sleep 5

# Check logs for synthetic bars
grep -E "SyntheticBarFallback" /tmp/futbot_server.log | tail -5

# Check for cached data loading
grep -E "Loading cached data|cached data loaded" /tmp/futbot_server.log | tail -5
```

### Expected Results
- ✅ **NO** `SyntheticBarFallback` logs
- ✅ **YES** "Loading cached data" messages
- ✅ Simulation completes successfully

### If Strict Mode Fails
- Should **STOP THE RUN** with clear error
- Should **NOT** silently continue with synthetic bars
- Error message should indicate missing cached data

---

## ✅ STEP 2: Verify Actual Price Integrity

### Purpose
Ensure cached bars = real market = Webull prices (~611 for QQQ, not ~488).

### Test Command
```bash
curl -s "http://localhost:8000/trades/roundtrips?symbol=QQQ&limit=5" | python3 -m json.tool
```

### Check These Fields
- `entry_price` - Should be ~611.xx (NOT ~488.xx)
- `exit_price` - Should be in 600-650 range
- `entry_time` - Valid timestamp
- `exit_time` - After entry_time

### Expected Results
```json
{
  "trades": [
    {
      "symbol": "QQQ",
      "entry_price": 611.20,  // ✅ Should be ~611, NOT ~488
      "exit_price": 613.80,
      "entry_time": "2025-11-26T14:35:00+00:00",
      "exit_time": "2025-11-26T15:05:00+00:00"
    }
  ]
}
```

### Validation Script
```bash
# Extract and check prices
curl -s "http://localhost:8000/trades/roundtrips?symbol=QQQ" | python3 -c "
import sys, json
data = json.load(sys.stdin)
trades = data.get('trades', [])
for t in trades[:3]:
    price = t.get('entry_price', 0)
    if 550 <= price <= 650:
        print(f'✅ Price OK: {price}')
    else:
        print(f'❌ Price WRONG: {price} (expected 550-650)')
"
```

---

## ✅ STEP 3: Cross-Check Price vs Webull

### Purpose
Manually verify prices match real market data.

### Steps
1. **Get a trade entry time:**
   ```bash
   curl -s "http://localhost:8000/trades/roundtrips?symbol=QQQ&limit=1" | python3 -c "
   import sys, json
   data = json.load(sys.stdin)
   trade = data.get('trades', [{}])[0]
   print(f'Entry Time: {trade.get(\"entry_time\")}')
   print(f'Entry Price: {trade.get(\"entry_price\")}')
   "
   ```

2. **Convert to EST:**
   - UTC time: `14:35:00` = `2:35 PM UTC`
   - EST time: `14:35 UTC` = `9:35 AM EST` (UTC-5)

3. **Check Webull:**
   - Open Webull
   - Navigate to QQQ 5-minute chart
   - Go to Nov 26, 2025
   - Find candle at `9:35 AM EST`
   - Check **close price** of that candle

4. **Compare:**
   - Webull price: `~611.20`
   - Your `entry_price`: `~611.20`
   - **Difference should be < $0.50** (slippage/timing)

### Success Criteria
- ✅ Prices match within $0.50
- ✅ If mismatch > $1.00, investigate data source

---

## ✅ STEP 4: Verify Trade Augmentation Works

### Purpose
Ensure regime/volatility metadata is captured and included in trades.

### Test Command
```bash
curl -s "http://localhost:8000/trades/roundtrips?symbol=QQQ&limit=1" | python3 -m json.tool
```

### Required Fields
Each trade must contain:
- ✅ `regime_at_entry` - e.g., "TREND", "COMPRESSION"
- ✅ `vol_bucket_at_entry` - e.g., "LOW", "MEDIUM", "HIGH"
- ✅ `agent` - e.g., "trend_agent", "ema_agent"
- ✅ `gross_pnl` - Dollar P&L
- ✅ `pnl_pct` - Percentage P&L
- ✅ `duration_minutes` - Trade duration

### Expected Structure
```json
{
  "trades": [
    {
      "symbol": "QQQ",
      "direction": "LONG",
      "entry_time": "2025-11-26T14:35:00+00:00",
      "entry_price": 611.20,
      "regime_at_entry": "TREND",           // ✅ Required
      "vol_bucket_at_entry": "MEDIUM",      // ✅ Required
      "exit_time": "2025-11-26T15:05:00+00:00",
      "exit_price": 613.80,
      "gross_pnl": 42.51,                   // ✅ Required
      "pnl_pct": 0.42,                      // ✅ Required
      "duration_minutes": 30.0,             // ✅ Required
      "reason": "Trend follow on strong EMA / ADX",
      "agent": "trend_agent"                // ✅ Required
    }
  ]
}
```

### Validation Script
```bash
curl -s "http://localhost:8000/trades/roundtrips?symbol=QQQ&limit=1" | python3 -c "
import sys, json
data = json.load(sys.stdin)
trades = data.get('trades', [])
if not trades:
    print('❌ No trades found')
    sys.exit(1)

trade = trades[0]
required = ['regime_at_entry', 'vol_bucket_at_entry', 'agent', 'gross_pnl', 'pnl_pct', 'duration_minutes']
missing = [f for f in required if trade.get(f) is None]

if missing:
    print(f'❌ Missing fields: {missing}')
    sys.exit(1)
else:
    print('✅ All required fields present')
    print(f'  Regime: {trade.get(\"regime_at_entry\")}')
    print(f'  Volatility: {trade.get(\"vol_bucket_at_entry\")}')
    print(f'  Agent: {trade.get(\"agent\")}')
"
```

---

## ✅ STEP 5: Verify Portfolio Manager Links Regime → Trade

### Purpose
Confirm regime engine, trading loop, portfolio manager, and round-trip endpoint are synchronized.

### Test Command
```bash
curl -s "http://localhost:8000/stats" | python3 -m json.tool
```

### Check These Fields
- `last_regime` - Current regime
- `last_volatility` - Current volatility level
- Compare with trade metadata for same timestamp

### Validation
```bash
# Get current regime
CURRENT_REGIME=$(curl -s "http://localhost:8000/stats" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('last_regime', 'UNKNOWN'))
")

# Get latest trade regime
TRADE_REGIME=$(curl -s "http://localhost:8000/trades/roundtrips?symbol=QQQ&limit=1" | python3 -c "
import sys, json
data = json.load(sys.stdin)
trades = data.get('trades', [])
if trades:
    print(trades[0].get('regime_at_entry', 'UNKNOWN'))
else:
    print('NO_TRADES')
")

echo "Current regime: $CURRENT_REGIME"
echo "Latest trade regime: $TRADE_REGIME"
```

### Expected Results
- ✅ Regime values are valid (TREND, COMPRESSION, etc.)
- ✅ Volatility values are valid (LOW, MEDIUM, HIGH)
- ✅ Values match between stats and trades

---

## 🎉 Success Criteria

**Phase 1 is 100% VALIDATED if:**

1. ✅ **No synthetic bars used** (strict mode working)
2. ✅ **Prices match Webull** (~611 for QQQ, not ~488)
3. ✅ **All trade fields present** (regime, volatility, P&L, duration)
4. ✅ **Regime synchronization** (stats match trades)
5. ✅ **No errors in logs**

---

## 🚀 Quick Validation Script

Run the automated validation:

```bash
./validate_phase1.sh
```

This script runs all checks automatically and reports results.

---

## 📊 Expected Runtime for Full-Day Backtest

Based on your current setup:

### Single Symbol (QQQ)
- **1-minute data** (390 bars/day) → **1-2 seconds**
- **5-minute data** (78 bars/day) → **0.5-1 second**

### Multiple Symbols (5 symbols)
- **1-minute data** (1,950 bars total) → **5-10 seconds**
- **5-minute data** (390 bars total) → **2-5 seconds**

### With Strict Mode
- Adds **+0.3-0.5 seconds** for data validation

### With Heavy Logging
- Current setup: **~10-15 seconds per day** for 5-minute data
- This is **NORMAL and EXCELLENT** performance

---

## 🔜 Next Steps After Validation

Once all checks pass:

1. ✅ **Lock Phase 1 as complete**
2. ✅ **Run full-day backtest benchmark**
3. ✅ **Multi-day regression (3-30 days)**
4. ✅ **Proceed to Phase 2: ML Regime Engine**

---

**Status:** Ready for validation ✅


