# Phase 1 Exit Criteria - Formal Definition

## 🎯 **Phase 1 PASSES when ALL criteria are met:**

### **1. P&L Accuracy (100% Required)**

#### **1.1 Package P&L = Sum of Legs**
**Metric:** # of packages with P&L mismatch > 0.5% between package P&L vs sum of legs
**Pass if:** = 0
- ✅ For every open multi-leg position:
  - `package_unrealized_pnl` = `call_unrealized_pnl` + `put_unrealized_pnl`
  - Tolerance: ±$0.01 or ±0.5% (whichever is larger)
- ✅ For every closed multi-leg trade:
  - `trade_total_pnl` = `call_pnl` + `put_pnl`
  - Tolerance: ±$0.01 or ±0.5% (whichever is larger)

#### **1.2 Cross-System Consistency**
**Metric:** # of positions/trades with P&L mismatch > 0.5% between UI vs API vs DB
**Pass if:** = 0
- ✅ UI P&L = API P&L = Database P&L
- ✅ Tolerance: ±$0.01 or ±0.5% (whichever is larger)
- ✅ Verified for all positions and trades

#### **1.3 Log vs Calculated**
**Metric:** # of exit events with P&L mismatch > 0.5% between logged vs calculated
**Pass if:** = 0
- ✅ Logged P&L matches calculated P&L
- ✅ Tolerance: ±$0.01 or ±0.5% (whichever is larger)
- ✅ Verified for all exit events

**Test:** Run reconciliation script, verify zero mismatches

---

### **2. Auto-Exit Trigger Accuracy (100% Required)**

#### **2.1 Theta Harvester Triggers**
- ✅ **TP (50%):** Fires in at least **2** trend-up days
- ✅ **SL (200%):** Fires in at least **1** fast-dump day
- ✅ **IV Collapse:** Fires in at least **1** IV-drop day (30%+ drop)
- ✅ **Regime Change:** Fires in at least **1** compression→expansion day

#### **2.2 Gamma Scalper Triggers**
- ✅ **TP (150%):** Fires in at least **2** big-move days
- ✅ **SL (50%):** Fires in at least **1** whipsaw day
- ✅ **GEX Reversal:** Fires in at least **1** GEX-flip day (negative→positive)
- ✅ **Time Limit:** Fires correctly at max hold time (390 bars)

#### **2.3 Trigger Timing**
- ✅ Triggers fire at correct thresholds (within 1% tolerance)
- ✅ No false positives (triggers when shouldn't)
- ✅ No false negatives (misses when should trigger)

**Test:** Run 3+ historical periods, verify all triggers fire correctly

---

### **3. Position Integrity (100% Required)**

#### **3.1 No Orphaned Legs**
**Metric:** # of broker orders missing package_id OR packages with missing leg
**Pass if:** = 0
- ✅ All multi-leg positions have both legs tracked
- ✅ No positions with only one leg
- ✅ No positions with missing leg data
- ✅ All broker orders have associated package_id

#### **3.2 No Stuck Packages**
**Metric:** # of positions stuck in "pending" state > 1000 bars
**Pass if:** = 0
- ✅ All positions either:
  - Close successfully (with exit reason)
  - Remain open with valid reason (e.g., "waiting for fill")
- ✅ No positions stuck in "pending" state indefinitely (>1000 bars)
- ✅ No positions with invalid state

#### **3.3 Exit Order Execution**
**Metric:** # of exit orders that fail to execute
**Pass if:** = 0
- ✅ All exit orders execute successfully
- ✅ Both legs close simultaneously
- ✅ No partial closes (unless intentional)

**Test:** Verify all positions in database have valid state

---

### **4. Error Handling (100% Required)**

#### **4.1 Zero Unhandled Exceptions**
**Metric:** # of stack traces in logs tagged ERROR/FATAL
**Pass if:** = 0
- ✅ No exceptions in logs over **N days** of simulation (N ≥ 3)
- ✅ All errors caught and logged with context
- ✅ System continues running after errors

#### **4.2 Partial Fill Handling**
- ✅ Partial fills handled gracefully
- ✅ Positions marked correctly
- ✅ Auto-exit waits for full fill
- ✅ No crashes on partial fills

#### **4.3 Order Rejection Handling**
- ✅ Rejected orders logged with reason
- ✅ Positions marked as "broken" or "needs review"
- ✅ Auto-exit disabled for broken positions
- ✅ Alerts generated for manual review

#### **4.4 Network Error Handling**
- ✅ Network errors caught and logged
- ✅ Retry logic works (with backoff)
- ✅ System continues running after errors
- ✅ Positions remain tracked during errors

**Test:** Review logs for exceptions, verify error handling

---

### **5. Deterministic Logging (100% Required)**

#### **5.1 Package Traceability**
- ✅ Every package has unique `multi_leg_id`
- ✅ Format: `{symbol}_{trade_type}_{direction}_{call_strike}_{put_strike}_{expiration}`
- ✅ ID logged at entry and exit

#### **5.2 Timestamps**
- ✅ Entry timestamp logged: `entry_time`
- ✅ Exit timestamp logged: `exit_time`
- ✅ Timestamps in ISO format
- ✅ Timezone consistent

#### **5.3 Leg Order IDs**
- ✅ Call leg order ID logged
- ✅ Put leg order ID logged
- ✅ Exit order IDs logged
- ✅ Order IDs match broker records (if applicable)

#### **5.4 Exit Reasons**
- ✅ Every exit has reason logged:
  - `"Theta Harvester TP: 50.0% profit"`
  - `"Theta Harvester SL: -200.0% loss"`
  - `"Theta Harvester IV collapse: ..."`
  - `"Theta Harvester regime exit: ..."`
  - `"Gamma Scalper TP: 150.0% profit"`
  - `"Gamma Scalper SL: -50.0% loss"`
  - `"Gamma Scalper GEX reversal: ..."`
  - `"Maximum hold time reached"`
- ✅ Reason included in trade record

**Test:** Verify all packages traceable, all exits have reasons

---

## 📊 **Test Requirements**

### **Minimum Test Coverage**
**Metric:** # of scenarios executed / # planned
**Pass if:** 100% of planned scenarios executed AND >= 80% passed, BUT all safety-critical scenarios MUST pass
- ✅ **3+ historical periods** tested:
  - 1 trending up
  - 1 trending down
  - 1 choppy/compressed
  - 1 major event (FOMC/CPI)
  - 1 options expiry week
- ✅ **10+ multi-leg positions** created
- ✅ **5+ auto-exit triggers** fired
- ✅ **3+ days** of simulation data

### **No-Day-From-Hell (NEW)**
**Metric:** # of days where realized sim loss exceeded pre-defined max_loss AND risk manager did not block further entries
**Pass if:** = 0
- ✅ Risk manager blocks entries when daily loss limit hit
- ✅ No days exceed max_loss without risk manager intervention
- ✅ All risk blocks logged and visible

### **Validation Scripts**
- ✅ Reconciliation script runs without errors
- ✅ API tests pass
- ✅ Unit tests pass
- ✅ UI tests pass (manual)

---

## ❌ **Phase 1 FAILS if ANY of the following occur:**

1. **P&L Mismatch:**
   - Package P&L ≠ Sum of legs (beyond tolerance)
   - UI P&L ≠ API P&L (beyond tolerance)
   - Log P&L ≠ Calculated P&L (beyond tolerance)

2. **Missing Triggers:**
   - Expected trigger doesn't fire
   - Trigger fires at wrong threshold
   - Trigger fires when shouldn't

3. **Position Issues:**
   - Orphaned legs found
   - Stuck packages found
   - Exit orders fail

4. **Unhandled Exceptions:**
   - Exceptions in logs
   - System crashes
   - Errors not caught

5. **Logging Issues:**
   - Missing package IDs
   - Missing timestamps
   - Missing exit reasons

---

## ✅ **Phase 1 PASS Checklist**

- [ ] **P&L Accuracy:** All checks pass
- [ ] **Auto-Exit Triggers:** All triggers fire correctly
- [ ] **Position Integrity:** No orphaned legs or stuck packages
- [ ] **Error Handling:** Zero unhandled exceptions
- [ ] **Deterministic Logging:** All packages traceable
- [ ] **Test Coverage:** Minimum requirements met
- [ ] **Validation Scripts:** All pass

**If ALL checked → Phase 1 PASSES → Proceed to Phase 2**

---

## 📝 **Phase 1 Results Template**

```
Phase 1 Validation Results
==========================

Date: [Date]
Tester: [Name]
Test Periods: [List periods tested]

P&L Accuracy:
- Package P&L = Sum of Legs: ✅ / ❌
- Cross-System Consistency: ✅ / ❌
- Log vs Calculated: ✅ / ❌

Auto-Exit Triggers:
- Theta Harvester TP: ✅ / ❌ (X occurrences)
- Theta Harvester SL: ✅ / ❌ (X occurrences)
- Theta Harvester IV Collapse: ✅ / ❌ (X occurrences)
- Theta Harvester Regime Change: ✅ / ❌ (X occurrences)
- Gamma Scalper TP: ✅ / ❌ (X occurrences)
- Gamma Scalper SL: ✅ / ❌ (X occurrences)
- Gamma Scalper GEX Reversal: ✅ / ❌ (X occurrences)
- Time Limit: ✅ / ❌ (X occurrences)

Position Integrity:
- No Orphaned Legs: ✅ / ❌
- No Stuck Packages: ✅ / ❌
- Exit Orders Execute: ✅ / ❌

Error Handling:
- Zero Unhandled Exceptions: ✅ / ❌
- Partial Fill Handling: ✅ / ❌
- Order Rejection Handling: ✅ / ❌
- Network Error Handling: ✅ / ❌

Deterministic Logging:
- Package Traceability: ✅ / ❌
- Timestamps: ✅ / ❌
- Leg Order IDs: ✅ / ❌
- Exit Reasons: ✅ / ❌

Issues Found:
- [List any issues]

Overall Result: ✅ PASS / ❌ FAIL

Next Steps:
- [If PASS] Proceed to Phase 2
- [If FAIL] Fix issues and retest
```

---

**Ready for Phase 1 validation!** 🚀

