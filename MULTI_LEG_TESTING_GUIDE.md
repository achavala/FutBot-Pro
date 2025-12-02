# Multi-Leg Execution Testing Guide

## ✅ Test Results

### Unit Tests: **ALL PASSED** ✅

```
✅ PASS: LegFill Calculation
✅ PASS: Multi-Leg P&L Calculation  
✅ PASS: Portfolio Manager
✅ PASS: Fill Tracking
```

All core data structures and calculations are working correctly.

---

## Testing Checklist

### Phase 1: Basic Functionality ✅ (Complete)

- [x] LegFill calculates total cost correctly
- [x] Multi-leg P&L calculation (combined across both legs)
- [x] Portfolio manager adds/closes multi-leg positions
- [x] Fill tracking for both legs independently
- [x] Credit/debit calculation for short/long positions

### Phase 2: API Endpoints

Run this to test API:
```bash
python3 test_multi_leg_api.py
```

Expected:
- `/options/positions` returns `multi_leg_positions` array
- `/trades/options/multi-leg` returns completed trades
- Both endpoints work without errors

### Phase 3: Live Trading Test

#### Step 1: Start the Server
```bash
python main.py --mode api --port 8000
```

#### Step 2: Open Dashboard
Navigate to: `http://localhost:8000/dashboard`

#### Step 3: Start Live Trading
Click **"Start Live"** button

#### Step 4: Monitor for Multi-Leg Trades

**For Theta Harvester (Straddles):**
- Wait for **COMPRESSION** regime
- Wait for **High IV** (>70th percentile)
- Should see log: `[THETA HARVEST] Compression + High IV → SELL STRADDLE`
- Check dashboard: Multi-leg position should appear

**For Gamma Scalper (Strangles):**
- Wait for **NEGATIVE GEX** regime
- Wait for **Low IV** (<30th percentile)
- Should see log: `[GAMMA SCALP] NEGATIVE GEX → BUY STRANGLE`
- Check dashboard: Multi-leg position should appear

#### Step 5: Verify in Dashboard

1. Go to **Analytics → Options Dashboard**
2. Check **"Multi-Leg Open Positions"** table:
   - Should show strategy (Theta Harvester / Gamma Scalper)
   - Should show call/put strikes
   - Should show credit/debit
   - Should show real-time P&L
   - Should show fill status

3. Check **"Multi-Leg Trade History"** table:
   - Should show completed trades
   - Should show combined P&L
   - Should show duration

#### Step 6: Test Auto-Exit

**Theta Harvester:**
- Position should auto-exit at 50% profit
- Position should auto-exit at 200% loss
- Position should auto-exit if IV collapses 30%+

**Gamma Scalper:**
- Position should auto-exit at 150% profit
- Position should auto-exit at 50% loss
- Position should auto-exit if GEX flips positive

---

## What to Look For

### ✅ Success Indicators

1. **Log Messages:**
   ```
   [MultiLeg] Executing SHORT STRADDLE 5x: CALL $673.00 @ $2.50 + PUT $673.00 @ $2.30
   [MultiLeg] CALL fill: 5 @ $2.50 (status: filled)
   [MultiLeg] PUT fill: 5 @ $2.30 (status: filled)
   [MultiLeg] STRADDLE position created: SPY_STRADDLE_short_673_673_20251126
   ```

2. **Dashboard:**
   - Multi-leg positions appear in table
   - Fill status shows "✅ Filled" for both legs
   - P&L updates in real-time
   - Trade history shows completed trades

3. **API Response:**
   ```json
   {
     "multi_leg_positions": [
       {
         "multi_leg_id": "SPY_STRADDLE_short_673_673_20251126",
         "trade_type": "straddle",
         "direction": "short",
         "call_strike": 673.0,
         "put_strike": 673.0,
         "combined_unrealized_pnl": 150.00,
         "both_legs_filled": true
       }
     ]
   }
   ```

### ❌ Error Indicators

1. **Missing Fills:**
   - If `both_legs_filled: false` persists
   - Check logs for order submission errors

2. **P&L Not Updating:**
   - Check if `update_positions()` is being called
   - Verify prices are being fetched correctly

3. **Auto-Exit Not Triggering:**
   - Check profit manager is initialized
   - Verify exit conditions are being checked
   - Check logs for exit check messages

---

## Manual Testing Commands

### Check API Endpoints

```bash
# Get all positions (including multi-leg)
curl http://localhost:8000/options/positions | python3 -m json.tool

# Get multi-leg trades
curl http://localhost:8000/trades/options/multi-leg?limit=10 | python3 -m json.tool

# Check live status
curl http://localhost:8000/live/status | python3 -m json.tool
```

### Monitor Logs

Watch for these log patterns:
```bash
# Multi-leg execution
grep -i "multileg\|straddle\|strangle" logs/*.log

# Fill tracking
grep -i "fill\|order" logs/*.log

# Auto-exit
grep -i "exit\|profit\|stop" logs/*.log
```

---

## Expected Behavior

### Theta Harvester (Straddle Seller)

**Entry:**
- Regime: COMPRESSION
- IV Percentile: >70%
- Action: SELL ATM straddle
- Expected Credit: ~$2-5 per contract

**Exit Conditions:**
- ✅ 50% profit: Exit when P&L = 50% of credit
- ✅ 200% loss: Exit when P&L = -200% of credit
- ✅ IV collapse: Exit if IV drops 30%+ from entry

### Gamma Scalper (Strangle Buyer)

**Entry:**
- GEX Regime: NEGATIVE
- GEX Strength: >$2B
- IV Percentile: <30%
- Action: BUY 25-delta strangle
- Expected Debit: ~$3-6 per contract

**Exit Conditions:**
- ✅ 150% profit: Exit when P&L = 150% of debit
- ✅ 50% loss: Exit when P&L = -50% of debit
- ✅ GEX reversal: Exit if GEX flips to positive

---

## Troubleshooting

### Issue: No Multi-Leg Positions Appearing

**Check:**
1. Are agents generating intents?
   ```bash
   # Check logs for agent activity
   grep -i "theta\|gamma" logs/*.log
   ```

2. Is executor receiving intents?
   ```bash
   grep -i "options.*execution\|multileg" logs/*.log
   ```

3. Are fills being tracked?
   - Check `both_legs_filled` status in API response
   - Check individual leg fill statuses

### Issue: Auto-Exit Not Working

**Check:**
1. Is profit manager initialized?
   - Check scheduler logs for "MultiLegProfitManager initialized"

2. Are exit checks running?
   ```bash
   grep -i "multileg.*exit\|should_take_profit" logs/*.log
   ```

3. Are exit conditions met?
   - Check current P&L percentage
   - Check IV change from entry
   - Check GEX regime change

### Issue: UI Not Updating

**Check:**
1. Is JavaScript console showing errors?
   - Open browser DevTools (F12)
   - Check Console tab

2. Are API calls succeeding?
   - Check Network tab in DevTools
   - Verify `/options/positions` returns 200

3. Is Options Dashboard tab visible?
   - Navigate to Analytics → Options Dashboard
   - Check if tables are populated

---

## Next Steps After Testing

Once basic functionality is verified:

1. **Monitor Performance:**
   - Track fill rates
   - Monitor P&L accuracy
   - Check auto-exit effectiveness

2. **Optimize:**
   - Adjust exit thresholds if needed
   - Fine-tune position sizing
   - Optimize fill tracking

3. **Scale:**
   - Test with multiple symbols
   - Test with larger position sizes
   - Test during different market conditions

---

## Test Scripts

1. **`test_multi_leg_simple.py`** - Unit tests (✅ PASSED)
2. **`test_multi_leg_api.py`** - API endpoint tests
3. **`test_multi_leg_execution.py`** - Full integration test (requires dependencies)

Run tests:
```bash
# Simple unit tests
python3 test_multi_leg_simple.py

# API tests (requires server running)
python3 test_multi_leg_api.py
```

---

## Status: ✅ Ready for Live Testing

All core functionality is implemented and unit tested. The system is ready for live trading tests with Theta Harvester and Gamma Scalper agents.


