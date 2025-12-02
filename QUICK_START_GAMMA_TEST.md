# Quick Start: Gamma-Only Test 🚀

## Three Simple Steps

### **Step 1: Freeze & Tag**

```bash
./FREEZE_AND_TAG.sh
```

**What it does:**
- Shows git status
- Asks for confirmation
- Commits all changes
- Creates tag: `v1.0.1-ml-gamma-qa`

**Or use helper:**
```bash
./EXECUTE_GAMMA_TEST.sh  # Runs freeze + starts test
```

---

### **Step 2: Start Gamma-Only Test**

```bash
GAMMA_ONLY_TEST_MODE=true ./START_VALIDATION.sh
```

**What to watch for in logs:**

✅ **Startup confirmation:**
```
🔬 GAMMA_ONLY_TEST_MODE=true (env var: true)
✅ Created X agents (Gamma Scalper only)
```

✅ **Gamma Scalper activity:**
```
[GAMMA SCALP] NEGATIVE GEX (...) → BUY Xx 25Δ strangle
[MultiLeg] STRANGLE position created: SPY_STRANGLE_long_...
[DeltaHedge] Hedging SELL X shares @ $Y
[DeltaHedge] Hedging BUY X shares @ $Y
[MultiLegExit] Closing STRANGLE: Gamma Scalper TP: 150.0% profit
```

**Let it run until:**
- At least 1-2 complete Gamma packages (entry → hedging → exit)
- On your chosen SPY/QQQ window (3-5 trading days)

---

### **Step 3: Export Timelines**

**In another terminal (while server is running):**

```bash
./EXPORT_TIMELINES.sh
```

**Or manually:**
```bash
curl -X POST http://localhost:8000/options/export-timelines | python3 -m json.tool
```

**Expected output:**
```json
{
  "status": "success",
  "run_id": "20241201_143022_SPY",
  "exported_count": 2,
  "output_dir": "phase1_results/gamma_only/20241201_143022_SPY"
}
```

**Check files:**
```bash
ls phase1_results/gamma_only/{run_id}/
cat phase1_results/gamma_only/{run_id}/*_timeline.txt | head -30
```

---

## Review Timeline

**Open one `*_timeline.txt` file and check:**

✅ **After each `hedge_executed` row:**
- `TotDelta` ≈ 0 (±0.05)
- Hedges spaced out (5-bar rule)
- No micro-hedges (< 5 shares)

✅ **P&L breakdown:**
- `OptP&L + HedgeP&L = TotP&L` (within rounding)
- On up-move: `OptP&L` positive, `HedgeP&L` negative, `TotP&L` net positive

✅ **At exit:**
- `hedge_shares` = 0
- `hedge_unrealized_pnl` ≈ 0
- Exit reason matches (TP/SL/time/GEX)

---

## Helper Scripts

- `EXECUTE_GAMMA_TEST.sh` - Runs freeze + starts test
- `EXPORT_TIMELINES.sh` - Exports timelines with nice output

---

**Ready to run!** 🚀

