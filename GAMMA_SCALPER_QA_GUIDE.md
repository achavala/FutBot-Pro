# Gamma Scalper QA Guide

## Overview

This guide provides step-by-step validation for Gamma Scalper delta hedging before Phase 1.

---

## Pre-Test Setup

### 1. Enable Timeline Logging

Timeline logging is automatically enabled in the scheduler. It logs:
- `bar`, `price`, `net_options_delta`, `hedge_shares`, `total_delta`
- `options_pnl`, `hedge_pnl`, `total_pnl`

### 2. Configure Focused Test

Run Gamma Scalper only (disable Theta Harvester):
- Single symbol: SPY or QQQ
- 3-5 days of intraday data
- Only Gamma Scalper agent active

---

## Test Scenarios

### **G-H1: Clean Up-Move with Re-Hedges**

**Setup:**
- Gamma Scalper buys long strangle (near ATM, delta ≈ 0)
- Underlying grinds up steadily

**Expected Timeline Pattern:**
```
Bar    Price    OptDelta  Hedge    TotDelta  OptP&L   HedgeP&L  TotP&L
100    $673.00  +0.00     +0.00    +0.00     $0.00    $0.00     $0.00
105    $675.00  +0.15     -15.00   +0.00     $+50.00  $-30.00   $+20.00
110    $677.00  +0.30     -30.00   +0.00     $+120.00 $-60.00   $+60.00
```

**Validation Checklist:**
- [ ] `price` increases
- [ ] `net_options_delta` becomes increasingly positive
- [ ] `hedge_shares` becomes increasingly short (negative) in steps
- [ ] `total_delta` stays near 0 (±0.05)
- [ ] `options_pnl` positive, `hedge_pnl` negative, `total_pnl` net positive
- [ ] Hedge trades spaced out (respecting 5-bar frequency limit)
- [ ] No hedge trades firing every bar

**Red Flags:**
- ❌ Hedge trades firing every bar (frequency limit not working)
- ❌ `total_delta` wandering far from 0 right after a hedge
- ❌ `hedge_pnl` larger than `options_pnl` (over-hedging)

---

### **G-H2: Up then Back Down (Round-Trip)**

**Setup:**
- Gamma Scalper buys long strangle
- Underlying moves up then back down over the same day

**Expected Timeline Pattern:**
```
Bar    Price    OptDelta  Hedge    TotDelta  OptP&L   HedgeP&L  TotP&L
100    $673.00  +0.00     +0.00    +0.00     $0.00    $0.00     $0.00
120    $678.00  +0.25     -25.00   +0.00     $+150.00 $-125.00  $+25.00
140    $673.00  +0.00     +0.00    +0.00     $+50.00  $-125.00  $-75.00
```

**Validation Checklist:**
- [ ] Start: small `net_options_delta`, `hedge_shares` ≈ 0
- [ ] Up move → increase short hedge
- [ ] Down move → hedge covers/reduces
- [ ] End: `hedge_shares` back near 0
- [ ] `total_pnl` positive (harvested gamma)
- [ ] No leftover hedge when options close

**Red Flags:**
- ❌ Ending with big leftover `hedge_shares` after options closed
- ❌ `hedge_realized_pnl` weirdly huge vs `options_pnl` (over-hedging)

---

### **G-H3: No Hedge Band / Frequency Limit**

**Setup:**
- Choppy path where delta pops above/below threshold often

**Expected Behavior:**
- Hedge trades spaced out (once per 5 bars minimum)
- Many small oscillations absorbed without constant trading
- `total_delta` oscillates a bit more, but trade count is reasonable

**Validation Checklist:**
- [ ] Hedge trades spaced out (respecting 5-bar frequency)
- [ ] No micro-hedges (< 5 shares)
- [ ] Reasonable hedge count for period
- [ ] `total_delta` oscillates but stays within reasonable band

**Red Flags:**
- ❌ Hedger firing on every small tick despite constraints
- ❌ Multiple hedges within same 5-bar window
- ❌ Excessive hedge trades (> 20 per day)

---

### **G-H4: Engine Restart Mid-Hedged**

**Setup:**
1. Run until:
   - Gamma Scalper has open options package
   - Non-zero `hedge_shares` for that symbol
2. Kill engine
3. Restart in same sim state
4. Watch first `_check_delta_hedging()` after restart

**Expected Behavior:**
- On restart, reconstructs:
  - Options position
  - Hedge position (shares + avg_price)
- First new hedge action is small adjustment, not giant reset
- `total_pnl` before and after restart is continuous (no jump)

**Validation Checklist:**
- [ ] State reloads correctly from database
- [ ] Hedge position reconstructed (shares + avg_price)
- [ ] Next hedge is adjustment, not reset
- [ ] P&L continuous across restart

**Red Flags:**
- ❌ On restart, thinks `hedge_shares = 0` and re-hedges full size
- ❌ P&L jumps at restart (state mismatch)

---

## Timeline Table Export

After each test, export timeline tables:

```python
# In scheduler or test script
from core.live.delta_hedge_logger import DeltaHedgeTimelineLogger

# Export timeline for a position
timeline_table = hedge_timeline_logger.export_timeline_table(multi_leg_id)
print(timeline_table)

# Save to file
with open(f"phase1_results/gamma_only/{multi_leg_id}_timeline.txt", "w") as f:
    f.write(timeline_table)
```

**Example Output:**
```
================================================================================
Delta Hedging Timeline: SPY_STRANGLE_long_680_665_20241126
================================================================================
Bar    Price    OptDelta   Hedge    TotDelta   OptP&L     HedgeP&L   TotP&L     Notes
--------------------------------------------------------------------------------
100    $673.00  +0.000     +0.00    +0.000     $+0.00     $+0.00     $+0.00     entry
105    $675.00  +0.150     -15.00   +0.000     $+50.00    $-30.00    $+20.00    hedge_executed
110    $677.00  +0.300     -30.00   +0.000     $+120.00   $-60.00    $+60.00    hedge_executed
================================================================================
```

---

## Guardrails Validation

### Daily Limits
- [ ] Max hedge trades per day: 50 (configurable)
- [ ] Max hedge notional per day: $100,000 (configurable)
- [ ] Limits enforced correctly

### Orphan Hedge Protection
- [ ] If options close but hedge remains, force flatten after 60 bars
- [ ] Alert logged when orphan detected
- [ ] Hedge position removed correctly

### Minimum Hedge Size
- [ ] No hedges < 5 shares
- [ ] Rounded to nearest share

---

## Success Criteria

### For Each Scenario:
- ✅ Timeline table shows expected pattern
- ✅ No red flags detected
- ✅ Hedge behavior matches expectations
- ✅ P&L calculations correct

### Overall:
- ✅ Delta hedging working correctly
- ✅ No over-trading
- ✅ No state mismatches
- ✅ Ready for full Phase 1

---

## Next Steps

1. **Run focused Gamma-only test** (3-5 days, single symbol)
2. **Export timeline tables** for each package
3. **Review tables** like a risk manager
4. **Fix any issues** found
5. **Proceed to full Phase 1** with Gamma + Theta

---

## Files

- `core/live/delta_hedge_logger.py` - Timeline logging
- `core/live/delta_hedge_manager.py` - Hedging logic (with guardrails)
- `scripts/test_gamma_only.py` - Focused test runner (TODO)
- `GAMMA_SCALPER_QA_GUIDE.md` - This guide

