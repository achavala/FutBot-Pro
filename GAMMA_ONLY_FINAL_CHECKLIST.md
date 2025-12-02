# Gamma-Only Test - Final Checklist

## ✅ Pre-Test Verification

### **1. Code State**
- [ ] All changes committed
- [ ] Tag created: `./FREEZE_AND_TAG.sh` or `git tag -a v1.0.1-ml-gamma-qa`
- [ ] Tag pushed to remote (optional)

### **2. Environment Setup**
- [ ] `GAMMA_ONLY_TEST_MODE` not set in production configs
- [ ] Test script sets env var: `./scripts/run_gamma_only_test.sh`
- [ ] Or manually: `export GAMMA_ONLY_TEST_MODE=true`

### **3. Configuration**
- [ ] Symbol: SPY or QQQ (single symbol)
- [ ] Period: 3-5 trading days (e.g., 2024-12-01 → 2024-12-05)
- [ ] Mode: SIM/historical
- [ ] Delta hedging config verified:
  - `delta_threshold: 0.10`
  - `min_hedge_shares: 5`
  - `max_hedge_trades_per_day: 50`
  - `max_hedge_notional_per_day: $100,000`
  - `max_orphan_hedge_bars: 60`

---

## 🚀 Test Execution

### **Step 1: Start Test**
```bash
# Option A: Via helper script
./scripts/run_gamma_only_test.sh

# Option B: Manual
GAMMA_ONLY_TEST_MODE=true ./START_VALIDATION.sh
```

**Verify in logs:**
- [ ] `🔬 GAMMA_ONLY_TEST_MODE=true` logged on startup
- [ ] `✅ Created X agents (Gamma Scalper only)` logged
- [ ] No Theta Harvester agents created

### **Step 2: Run Simulation**
- [ ] Simulation starts successfully
- [ ] Wait for 1-2 complete Gamma Scalper packages:
  - Entry (strangle open)
  - Multiple hedges (at least 2-3 hedge trades)
  - Exit (TP/SL/GEX/TIME)

**Monitor logs for:**
- [ ] `[GAMMA SCALP] NEGATIVE GEX (...) → BUY Xx 25Δ strangle`
- [ ] `[MultiLeg] STRANGLE position created: ...`
- [ ] `[DeltaHedge] Hedging SELL X shares @ $Y`
- [ ] `[DeltaHedge] Hedging BUY X shares @ $Y`
- [ ] `[MultiLegExit] Closing STRANGLE: ...`

### **Step 3: Export Timelines**
```bash
curl -X POST http://localhost:8000/options/export-timelines
```

**Verify response:**
- [ ] `"status": "success"`
- [ ] `"exported_count" > 0` (or 0 with clear message if no packages)
- [ ] `"run_id"` returned (e.g., `"20241201_143022_SPY"`)
- [ ] `"output_dir"` path correct

**Check files:**
- [ ] `phase1_results/gamma_only/{run_id}/` directory exists
- [ ] `{multi_leg_id}_timeline.txt` files present
- [ ] `{multi_leg_id}_metrics.json` files present
- [ ] `all_timelines_summary.txt` present
- [ ] `run_metadata.json` present

---

## 📊 Timeline Review

### **For Each Timeline File**

Open `{multi_leg_id}_timeline.txt` and verify:

#### **Delta Behavior**
- [ ] `OptDelta` moves with price as expected
- [ ] After each `hedge_executed`: `TotDelta` ≈ 0 (±0.05)
- [ ] Between hedges: `TotDelta` drifts but stays bounded (±0.20)

#### **Hedge Trade Frequency**
- [ ] Hedge rows spaced out (respecting 5-bar frequency limit)
- [ ] No micro-hedges (`hedge_shares` ≥ 5 shares)
- [ ] Hedge count ≤ 50 per day (check `hedge_count` in metrics)
- [ ] Notional < $100k per day (check `total_shares_traded * price`)

#### **P&L Breakdown**
- [ ] Row-by-row: `OptP&L + HedgeP&L = TotP&L` (within rounding)
- [ ] On up-move: `options_pnl` positive, `hedge_pnl` negative, `total_pnl` net positive
- [ ] On round-trip: `total_pnl` positive (harvested gamma)
- [ ] At exit: `hedge_unrealized_pnl` ≈ 0
- [ ] At exit: `hedge_shares` ≈ 0 (positions flat)

#### **Exit Reasons**
- [ ] Final row shows sensible exit reason:
  - `TP_150` (take profit at 150%)
  - `SL_50` (stop loss at 50%)
  - `TIME_LIMIT` (max hold time)
  - `GEX_REVERSAL` (GEX flipped)
- [ ] P&L at exit matches trigger (e.g., TP=150% → `total_pnl` ≈ 150% of debit)

---

## 🔍 Guardrails Validation

### **Daily Limits**
- [ ] `hedge_trades_per_day` < 50 (check logs/metrics)
- [ ] `hedge_notional_per_day` < $100k (check logs/metrics)
- [ ] Limits enforced correctly (no limit exceeded)

### **Orphan Hedge Protection**
- [ ] If options close but hedge remains, auto-flatten after 60 bars
- [ ] Alert logged: `⚠️ [DeltaHedge] ... ORPHAN_HEDGE_FLATTEN`
- [ ] Hedge position removed correctly

### **Minimum Hedge Size**
- [ ] No hedges < 5 shares (check timeline for `hedge_shares` values)
- [ ] Rounded to nearest share

---

## ✅ Success Criteria

### **For Each Scenario (G-H1 through G-H4)**

- [ ] Timeline table shows expected pattern
- [ ] No red flags detected
- [ ] Hedge behavior matches expectations
- [ ] P&L calculations correct

### **Overall**
- [ ] Delta hedging working correctly
- [ ] No over-trading
- [ ] No state mismatches
- [ ] Ready for full Phase 1

---

## 📝 Documentation

### **Update QA Guide**
- [ ] Mark scenarios as PASSED in `GAMMA_SCALPER_QA_GUIDE.md`
- [ ] Reference: `multi_leg_id`, date, file name
- [ ] Note any issues found

### **Create Test Report**
- [ ] Document test period (dates, symbol)
- [ ] List packages tested (multi_leg_ids)
- [ ] Summary of findings
- [ ] Any issues or edge cases

---

## 🔄 Next Steps

### **After Gamma-Only Test Passes**

1. **Switch Back to Full Mode**
   ```bash
   # Unset env var (or don't set it)
   ./START_VALIDATION.sh  # Normal mode: Theta + Gamma
   ```

2. **Run Full Phase 1**
   - Use `PHASE_1_VALIDATION_CHECKLIST.md`
   - Run 3 historical periods
   - Execute Theta + Gamma scenarios
   - Score using `PHASE_1_EXIT_CRITERIA.md`

---

## 🐛 Troubleshooting

### **No Timelines Exported**
- Check: Are there any Gamma Scalper packages?
- Check: `GET /options/hedge-timelines` returns summaries
- Check: Logs for `[GAMMA SCALP]` entries

### **Timeline Tables Empty**
- Check: Timeline logger enabled in scheduler
- Check: `hedge_timeline_logger` initialized
- Check: Multi-leg positions exist

### **Import Errors**
- Check: `scripts/__init__.py` exists
- Check: PYTHONPATH includes project root
- Check: Virtual environment activated

---

**Ready to test!** 🚀

