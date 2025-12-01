# Price Mismatch Diagnosis: QQQ 611 vs 488

## 🔍 Issue Summary

**Problem:** QQQ shows ~611 on Webull (Nov 26, 2025) but trades are executed at ~488 in the system.

**Gap:** ~20% difference (123 points) - This is significant and indicates a structural issue.

---

## 📊 Current Trade Data Analysis

From trade log inspection:
- **Trade Prices:** 450-488 range
- **Trade Times:** Nov 26, 2025 14:31-15:06 UTC
- **Issue:** Some trades show backwards timestamps (entry_time after exit_time)

### Sample Trade Issues:
```json
{
  "entry_time": "2025-11-26T15:06:00+00:00",
  "exit_time": "2025-11-26T14:34:00+00:00",  // ⚠️ Exit BEFORE entry!
  "entry_price": 2382.81,  // ⚠️ Extremely high
  "exit_price": 397.36
}
```

---

## 🔍 Root Cause Analysis

### Likely Causes (in order of probability):

#### 1. **Missing Historical Data → Synthetic Bars**
- **Symptom:** Cache shows no QQQ data for Nov 26, 2025
- **Impact:** System falls back to synthetic bar generation
- **Synthetic bars** use a base price that may be incorrect or from a different date
- **Fix:** Need to collect actual QQQ data for Nov 26, 2025

#### 2. **Wrong Date/Year in Data**
- **Symptom:** Data might be from 2024 instead of 2025
- **Impact:** QQQ was ~$488 in late 2024, ~$611 in late 2025
- **Fix:** Verify date alignment in data collection

#### 3. **Price Source Issue**
- **Current:** Uses `bar.close` for execution price (line 860 in scheduler.py)
- **Issue:** If bar data is wrong, execution price is wrong
- **Fix:** Verify bar data source and price fields

#### 4. **Timestamp/Timezone Mismatch**
- **Symptom:** Backwards timestamps in some trades
- **Impact:** Trades recorded with wrong entry/exit times
- **Fix:** Fix timestamp handling in portfolio manager

---

## ✅ Diagnostic Steps

### Step 1: Verify Data Availability
```bash
# Check what data exists in cache
python3 -c "
import sqlite3
import pandas as pd
conn = sqlite3.connect('data/cache.db')
# Check QQQ data dates and prices
"
```

### Step 2: Check if Synthetic Bars Are Used
```bash
# Look for synthetic bar generation in logs
grep -i "synthetic" /tmp/futbot_server.log
```

### Step 3: Compare Bar Prices vs Trade Prices
- Get a bar at trade time from cache
- Compare bar.close vs trade entry_price
- If they match → data source issue
- If they differ → execution price selection issue

### Step 4: Verify Date Alignment
- Check Webull date: Nov 26, 2025
- Check system date: What date is actually being used?
- Check timezone: UTC vs EST conversion

---

## 🔧 Fixes Needed

### Fix 1: Collect Correct QQQ Data
**Action:** Re-run data collection for QQQ on Nov 26, 2025
```bash
python3 scripts/collect_historical_data.py --stocks QQQ --start-date 2025-11-26 --end-date 2025-11-27
```

### Fix 2: Fix Timestamp Issues
**Action:** Fix backwards timestamps in trade recording
- Location: `core/portfolio/manager.py` - `close_position()` and `apply_position_delta()`
- Issue: Entry/exit times may be swapped in some cases

### Fix 3: Add Price Validation
**Action:** Add validation to ensure prices are reasonable
- Check: Price within expected range (e.g., QQQ should be 400-700 in 2025)
- Alert: If price is outside expected range, log warning

### Fix 4: Improve Synthetic Bar Base Price
**Action:** If synthetic bars are used, use more accurate base price
- Current: Uses last cached price or arbitrary base
- Better: Use actual market price from data source if available

---

## 📋 Implementation Plan

1. **Immediate:** Check if QQQ data exists for Nov 26, 2025
2. **If Missing:** Collect QQQ data for that date
3. **Fix:** Timestamp issues in trade recording
4. **Add:** Price validation and warnings
5. **Create:** Round-trip trade view endpoint (see separate task)

---

## 🎯 Expected Outcome

After fixes:
- ✅ QQQ trades execute at ~611 (matching Webull)
- ✅ No backwards timestamps
- ✅ Accurate entry/exit times
- ✅ Correct P&L calculations

---

**Status:** 🔍 **INVESTIGATION IN PROGRESS**


