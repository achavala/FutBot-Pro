# Gamma-Only Test - Do This Next ✅

## Quick Start Checklist

### **Step 1: Freeze This State**

```bash
./FREEZE_AND_TAG.sh
```

**Or explicitly:**
```bash
./FREEZE_AND_TAG.sh v1.0.1-ml-gamma-qa "Gamma-only QA infra complete"
```

**Verify:**
```bash
git status              # should be clean
git show v1.0.1-ml-gamma-qa --stat
```

---

### **Step 2: Run Gamma-Only Simulation**

```bash
GAMMA_ONLY_TEST_MODE=true ./START_VALIDATION.sh
```

**In logs, confirm you see:**
- ✅ `🔬 GAMMA_ONLY_TEST_MODE=true (env var: true)`
- ✅ `✅ Created X agents (Gamma Scalper only)`

**Let it run:**
- Over your pre-chosen SPY/QQQ 3-5 day window
- Until at least 1-2 Gamma packages complete (entry → hedging → exit)

**Monitor logs for:**
- `[GAMMA SCALP] NEGATIVE GEX (...) → BUY Xx 25Δ strangle`
- `[MultiLeg] STRANGLE position created: ...`
- `[DeltaHedge] Hedging SELL X shares @ $Y`
- `[DeltaHedge] Hedging BUY X shares @ $Y`
- `[MultiLegExit] Closing STRANGLE: ...`

---

### **Step 3: Export Timelines**

```bash
curl -X POST http://localhost:8000/options/export-timelines
```

**Response should include:**
```json
{
  "status": "success",
  "run_id": "20241201_143022_SPY",
  "exported_count": 2,
  "output_dir": "phase1_results/gamma_only/20241201_143022_SPY"
}
```

**Then check:**
```bash
ls phase1_results/gamma_only/{run_id}/
```

**You should see:**
- ✅ One or more `*_timeline.txt` files
- ✅ `*_metrics.json` files
- ✅ `all_timelines_summary.txt`
- ✅ `run_metadata.json`

---

### **Step 4: Review 1-2 Packages Like a Risk Manager**

**Open one timeline file and sanity-check:**

#### **After each `hedge_executed` row:**
- [ ] `TotDelta` ≈ 0 (±0.05)
- [ ] Hedge rows spaced out (respect 5-bar / min-size rules)
- [ ] No micro-hedges (< 5 shares)

#### **For trending paths:**
- [ ] `OptP&L` > 0
- [ ] `HedgeP&L` < 0
- [ ] `TotP&L` > 0 (net positive)

#### **At exit:**
- [ ] No remaining `hedge_shares` (≈ 0)
- [ ] `Hedge unrealized` ≈ 0
- [ ] Exit reason matches rules (TP/SL/time/GEX)

**Then mark scenarios in `GAMMA_SCALPER_QA_GUIDE.md` as PASSED:**
- Reference: `run_id`, `multi_leg_id`, date, file name

---

### **Step 5: Switch Back and Start Full Phase 1**

**When you're happy with Gamma-only behavior:**

```bash
# Run without the env var (or explicitly set to false)
./START_VALIDATION.sh
```

**Then follow your existing:**
- `PHASE_1_VALIDATION_CHECKLIST.md`
- `PHASE_1_EXIT_CRITERIA.md`

**For the full Theta + Gamma system across your 3 periods.**

---

## Expected Timeline Table Format

```
================================================================================
Delta Hedging Timeline: SPY_STRANGLE_long_680_665_20241126
================================================================================
Bar    Price    OptDelta   Hedge    TotDelta   OptP&L     HedgeP&L   TotP&L     Notes
--------------------------------------------------------------------------------
100    $673.00  +0.000     +0.00    +0.000     $+0.00     $+0.00     $+0.00     entry
105    $675.00  +0.150     -15.00   +0.000     $+50.00    $-30.00    $+20.00    hedge_executed
110    $677.00  +0.300     -30.00   +0.000     $+120.00   $-60.00    $+60.00    hedge_executed
115    $673.00  +0.000     +0.00    +0.000     $+50.00    $-60.00    $-10.00    hedge_executed
120    $670.00  -0.150     +15.00   +0.000     $+20.00    $-45.00    $-25.00    hedge_executed
125    $673.00  +0.000     +0.00    +0.000     $+50.00    $-45.00    $+5.00     exit_TP_150
================================================================================
```

---

## Success Criteria

### **For Each Package:**
- ✅ Timeline table shows expected pattern
- ✅ No red flags detected
- ✅ Hedge behavior matches expectations
- ✅ P&L calculations correct

### **Overall:**
- ✅ Delta hedging working correctly
- ✅ No over-trading
- ✅ No state mismatches
- ✅ Ready for full Phase 1

---

## Troubleshooting

### **No timelines exported:**
- Check: Are there any Gamma Scalper packages?
- Check: `GET /options/hedge-timelines` returns summaries
- Check: Logs for `[GAMMA SCALP]` entries

### **Timeline tables empty:**
- Check: Timeline logger enabled in scheduler
- Check: `hedge_timeline_logger` initialized
- Check: Multi-leg positions exist

### **Import errors:**
- Check: `scripts/__init__.py` exists
- Check: PYTHONPATH includes project root
- Check: Virtual environment activated

---

**Ready to test!** 🚀

