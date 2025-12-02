# Run Gamma-Only Test Now 🚀

## Step-by-Step Execution Guide

### **Step 1: Freeze Current State**

```bash
./FREEZE_AND_TAG.sh
```

**Expected output:**
- Shows git status
- Asks for confirmation
- Creates tag: `v1.0.1-ml-gamma-qa`

**Verify:**
```bash
git status              # should be clean
git show v1.0.1-ml-gamma-qa --stat
```

---

### **Step 2: Start Gamma-Only Simulation**

```bash
GAMMA_ONLY_TEST_MODE=true ./START_VALIDATION.sh
```

**While it's running, confirm in logs:**

✅ Look for these lines:
```
🔬 GAMMA_ONLY_TEST_MODE=true (env var: true)
✅ Created X agents (Gamma Scalper only)
```

**Monitor logs for Gamma Scalper activity:**
```
[GAMMA SCALP] NEGATIVE GEX (...) → BUY Xx 25Δ strangle
[MultiLeg] STRANGLE position created: SPY_STRANGLE_long_...
[DeltaHedge] Hedging SELL X shares @ $Y
[DeltaHedge] Hedging BUY X shares @ $Y
[MultiLegExit] Closing STRANGLE: Gamma Scalper TP: 150.0% profit
```

**Let it run until:**
- At least 1-2 complete Gamma Scalper packages (entry → hedging → exit)
- On your chosen SPY/QQQ window (3-5 trading days)

---

### **Step 3: Export Timelines**

**In another terminal (while simulation is running or after it completes):**

```bash
curl -X POST http://localhost:8000/options/export-timelines
```

**Expected response:**
```json
{
  "status": "success",
  "run_id": "20241201_143022_SPY",
  "exported_count": 2,
  "output_dir": "phase1_results/gamma_only/20241201_143022_SPY"
}
```

**If `exported_count` is 0:**
- Let the sim run longer
- Wait for at least one Gamma package to complete
- Call export again

**Check files:**
```bash
ls phase1_results/gamma_only/{run_id}/
```

**You should see:**
- `*_timeline.txt` files (one per package)
- `*_metrics.json` files
- `all_timelines_summary.txt`
- `run_metadata.json`

---

### **Step 4: Manually Review Timeline**

**Pick one `*_timeline.txt` file and open it:**

**Check after each `hedge_executed` row:**

✅ **Delta Behavior:**
- `TotDelta` ≈ 0 (±0.05)
- Hedges spaced out (not every bar, respect 5-bar rule)
- No hedges smaller than 5 shares

✅ **P&L Breakdown:**
- `OptP&L + HedgeP&L = TotP&L` row by row (within rounding)
- On up-move: `OptP&L` positive, `HedgeP&L` negative, `TotP&L` net positive

✅ **At final row:**
- `hedge_shares` = 0 (positions flat)
- `hedge_unrealized_pnl` ≈ 0
- `total_pnl` matches exit reason (TP/SL/time/GEX)

**Example timeline pattern:**
```
Bar    Price    OptDelta   Hedge    TotDelta   OptP&L     HedgeP&L   TotP&L     Notes
--------------------------------------------------------------------------------
100    $673.00  +0.000     +0.00    +0.000     $+0.00     $+0.00     $+0.00     entry
105    $675.00  +0.150     -15.00   +0.000     $+50.00    $-30.00    $+20.00    hedge_executed
110    $677.00  +0.300     -30.00   +0.000     $+120.00   $-60.00    $+60.00    hedge_executed
115    $673.00  +0.000     +0.00    +0.000     $+50.00    $-60.00    $-10.00    hedge_executed
120    $670.00  -0.150     +15.00   +0.000     $+20.00    $-45.00    $-25.00    hedge_executed
125    $673.00  +0.000     +0.00    +0.000     $+50.00    $-45.00    $+5.00     exit_TP_150
```

**If timeline looks sane:**

✅ **Update `GAMMA_SCALPER_QA_GUIDE.md`:**

Mark scenarios as PASSED:
- G-H1: Clean up-move with re-hedges
- G-H2: Up then back down (round-trip)
- G-H3: No hedge band / frequency limit

**Reference:**
- `run_id`: `20241201_143022_SPY`
- `multi_leg_id`: `SPY_STRANGLE_long_680_665_20241126`
- `filename`: `SPY_STRANGLE_long_680_665_20241126_timeline.txt`

---

### **Step 5: Switch Back to Full System**

**When you're happy with Gamma-only behavior:**

```bash
# Normal full system (Theta + Gamma)
./START_VALIDATION.sh
```

**Then follow:**
- `PHASE_1_VALIDATION_CHECKLIST.md`
- `PHASE_1_EXIT_CRITERIA.md`

**For the full Theta + Gamma system across your 3 periods.**

---

## Quick Reference

### **Start Test**
```bash
./FREEZE_AND_TAG.sh
GAMMA_ONLY_TEST_MODE=true ./START_VALIDATION.sh
```

### **Export Timelines**
```bash
curl -X POST http://localhost:8000/options/export-timelines
```

### **Check Files**
```bash
ls phase1_results/gamma_only/{run_id}/
cat phase1_results/gamma_only/{run_id}/*_timeline.txt
```

### **Get Timeline Summaries**
```bash
curl http://localhost:8000/options/hedge-timelines | python3 -m json.tool
```

---

## Success Criteria

### **For Each Timeline:**
- ✅ `TotDelta` ≈ 0 after each hedge
- ✅ Hedges spaced out (5-bar rule respected)
- ✅ No micro-hedges (< 5 shares)
- ✅ P&L breakdown correct
- ✅ Flat hedge at exit

### **Overall:**
- ✅ Delta hedging working correctly
- ✅ No over-trading
- ✅ Ready for full Phase 1

---

**Ready to run!** 🚀

