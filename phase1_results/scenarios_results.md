# Phase 1 Scenario Results

**Template for tracking scenario execution and results**

---

## Period: [trending_up / trending_down / choppy / major_event / expiry_week]

**Dates:** YYYY-MM-DD → YYYY-MM-DD  
**Run ID:** run_YYYYMMDD_HHMMSS  
**Git Tag:** v1.0.0-ml-multi-leg (or later fix tag)

---

## Scenario Execution Log

### Theta Harvester Scenarios

#### A1. Normal Green Day → TP at +50%
- [ ] **Executed:** Yes/No
- [ ] **Pass/Fail:** Pass / Fail
- **Package ID:** `[multi_leg_id]`
- **Entry Time:** YYYY-MM-DD HH:MM:SS
- **Exit Time:** YYYY-MM-DD HH:MM:SS
- **Entry P&L:** $X.XX
- **Exit P&L:** $X.XX (%)
- **Exit Reason:** `[reason from logs]`
- **Notes:** [Any observations]

#### A2. Fast Dump → SL at -200%
- [ ] **Executed:** Yes/No
- [ ] **Pass/Fail:** Pass / Fail
- **Package ID:** `[multi_leg_id]`
- **Entry Time:** YYYY-MM-DD HH:MM:SS
- **Exit Time:** YYYY-MM-DD HH:MM:SS
- **Entry P&L:** $X.XX
- **Exit P&L:** $X.XX (%)
- **Exit Reason:** `[reason from logs]`
- **Notes:** [Any observations]

#### A3. IV Collapse → Exit on IV Rule
- [ ] **Executed:** Yes/No
- [ ] **Pass/Fail:** Pass / Fail
- **Package ID:** `[multi_leg_id]`
- **Entry Time:** YYYY-MM-DD HH:MM:SS
- **Exit Time:** YYYY-MM-DD HH:MM:SS
- **Entry IV:** X.XX%
- **Exit IV:** X.XX%
- **IV Drop:** X.XX%
- **Exit Reason:** `[reason from logs]`
- **Notes:** [Any observations]

#### A4. Regime Change → Exit on Regime
- [ ] **Executed:** Yes/No
- [ ] **Pass/Fail:** Pass / Fail
- **Package ID:** `[multi_leg_id]`
- **Entry Regime:** [compression]
- **Exit Regime:** [expansion/trend]
- **Exit Reason:** `[reason from logs]`
- **Notes:** [Any observations]

---

### Gamma Scalper Scenarios

#### B1. Big Move → TP at +150%
- [ ] **Executed:** Yes/No
- [ ] **Pass/Fail:** Pass / Fail
- **Package ID:** `[multi_leg_id]`
- **Entry Time:** YYYY-MM-DD HH:MM:SS
- **Exit Time:** YYYY-MM-DD HH:MM:SS
- **Entry P&L:** $X.XX
- **Exit P&L:** $X.XX (%)
- **Exit Reason:** `[reason from logs]`
- **Notes:** [Any observations]

#### B2. Whipsaw → SL at -50%
- [ ] **Executed:** Yes/No
- [ ] **Pass/Fail:** Pass / Fail
- **Package ID:** `[multi_leg_id]`
- **Entry Time:** YYYY-MM-DD HH:MM:SS
- **Exit Time:** YYYY-MM-DD HH:MM:SS
- **Entry P&L:** $X.XX
- **Exit P&L:** $X.XX (%)
- **Exit Reason:** `[reason from logs]`
- **Notes:** [Any observations]

#### B3. GEX Reversal → Exit on GEX Rule
- [ ] **Executed:** Yes/No
- [ ] **Pass/Fail:** Pass / Fail
- **Package ID:** `[multi_leg_id]`
- **Entry GEX:** -X.XXB (NEGATIVE)
- **Exit GEX:** +X.XXB (POSITIVE)
- **Exit Reason:** `[reason from logs]`
- **Notes:** [Any observations]

#### B4. Time-Limit Exit → Exit at Max Hold Time
- [ ] **Executed:** Yes/No
- [ ] **Pass/Fail:** Pass / Fail
- **Package ID:** `[multi_leg_id]`
- **Bars Held:** XXX
- **Max Bars:** 390
- **Exit Reason:** `[reason from logs]`
- **Notes:** [Any observations]

---

## Edge Cases

### E1. Partial Fill on One Leg
- [ ] **Executed:** Yes/No
- [ ] **Pass/Fail:** Pass / Fail
- **Package ID:** `[multi_leg_id]`
- **Call Fill Status:** [filled/partially_filled]
- **Put Fill Status:** [filled/partially_filled]
- **Auto-Exit Behavior:** [waited for full fill / blocked]
- **Notes:** [Any observations]

### E2. One Leg Rejected
- [ ] **Executed:** Yes/No
- [ ] **Pass/Fail:** Pass / Fail
- **Package ID:** `[multi_leg_id]`
- **Rejected Leg:** [call/put]
- **Rejection Reason:** [reason from broker]
- **Position Status:** [broken/needs_review]
- **Notes:** [Any observations]

### E3. Network Error During Close
- [ ] **Executed:** Yes/No
- [ ] **Pass/Fail:** Pass / Fail
- **Package ID:** `[multi_leg_id]`
- **Error Type:** [network timeout / API error]
- **Retry Behavior:** [retried X times / failed]
- **Recovery:** [recovered / manual intervention]
- **Notes:** [Any observations]

### E4. Multiple Packages Per Symbol
- [ ] **Executed:** Yes/No
- [ ] **Pass/Fail:** Pass / Fail
- **Symbol:** [SPY/QQQ]
- **Package IDs:** `[id1, id2, ...]`
- **Independent Tracking:** [Yes/No]
- **No Conflicts:** [Yes/No]
- **Notes:** [Any observations]

### E5. Signal Flips Multiple Times
- [ ] **Executed:** Yes/No
- [ ] **Pass/Fail:** Pass / Fail
- **First Package ID:** `[multi_leg_id]`
- **Second Package ID:** `[multi_leg_id]`
- **No Duplicate IDs:** [Yes/No]
- **No State Leakage:** [Yes/No]
- **Notes:** [Any observations]

### E6. Engine Restart Mid-Trade
- [ ] **Executed:** Yes/No
- [ ] **Pass/Fail:** Pass / Fail
- **Package ID:** `[multi_leg_id]`
- **State Reloaded:** [Yes/No]
- **Auto-Exit Resumed:** [Yes/No]
- **No Double Entry:** [Yes/No]
- **No Lost Exit:** [Yes/No]
- **Notes:** [Any observations]

### E7. Clock/Time Anomalies
- [ ] **Executed:** Yes/No
- [ ] **Pass/Fail:** Pass / Fail
- **Anomaly Type:** [DST / weekend gap / market hours boundary]
- **No Trades in Closed Markets:** [Yes/No]
- **Time-Based Exits Fire:** [Yes/No]
- **Timestamps Consistent:** [Yes/No]
- **Notes:** [Any observations]

---

## Summary

**Total Scenarios:** X / Y executed  
**Passed:** X  
**Failed:** Y  
**Pass Rate:** X%  

**Critical Issues:** [List any critical issues found]

**Ready for Next Period:** [Yes/No]

