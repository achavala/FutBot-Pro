# Gamma Scalper Only Test Guide

## Overview

This guide walks through running a focused Gamma Scalper test with delta hedging validation.

---

## Step 1: Configure Gamma-Only Test

### **Option A: Via Code (Recommended)**

Modify `ui/fastapi_app.py` `_initialize_bot_manager()` to use Gamma-only agents:

```python
# In _initialize_bot_manager(), replace agents creation with:
from scripts.create_gamma_only_agents import create_gamma_only_agents

agents = create_gamma_only_agents(
    symbol=symbol,
    options_data_feed=options_data_feed,
    options_broker_client=options_broker_client,
)
```

### **Option B: Via API (After Start)**

After starting live trading, you can replace agents:

```python
# Via API or code
from scripts.create_gamma_only_agents import create_gamma_only_agents
bot_manager.live_loop.agents = create_gamma_only_agents('SPY', ...)
```

### **Verify Configuration**

Check delta hedging config:
```bash
python3 << 'EOF'
from core.live.delta_hedge_manager import DeltaHedgeConfig

config = DeltaHedgeConfig()
print(f"✅ Delta Hedging Config:")
print(f"   delta_threshold: {config.delta_threshold}")
print(f"   min_hedge_shares: {config.min_hedge_shares}")
print(f"   max_hedge_trades_per_day: {config.max_hedge_trades_per_day}")
print(f"   max_hedge_notional_per_day: ${config.max_hedge_notional_per_day:,.0f}")
print(f"   max_orphan_hedge_bars: {config.max_orphan_hedge_bars}")
EOF
```

---

## Step 2: Start Test Run

```bash
./START_VALIDATION.sh
```

**Configuration:**
- Symbol: SPY (or QQQ)
- Period: 3-5 trading days (e.g., 2024-12-01 → 2024-12-05)
- Mode: SIM/historical
- Agents: Gamma Scalper only (Theta Harvester disabled)

---

## Step 3: Collect Complete Packages

Wait for at least 1-2 complete Gamma Scalper packages:

**For each package, you need:**
- ✅ Entry (strangle open)
- ✅ Multiple hedges (at least 2-3 hedge trades)
- ✅ Exit (TP/SL/GEX/TIME)

**Monitor logs for:**
```
[GAMMA SCALP] NEGATIVE GEX (...) → BUY Xx 25Δ strangle
[MultiLeg] STRANGLE position created: SPY_STRANGLE_long_...
[DeltaHedge] Hedging SELL X shares @ $Y
[DeltaHedge] Hedging BUY X shares @ $Y
[MultiLegExit] Closing STRANGLE: Gamma Scalper TP: 150.0% profit
```

---

## Step 4: Export Timeline Tables

### **Via API (After Simulation)**

```bash
# Get timelines
curl http://localhost:8000/options/hedge-timelines | python3 -m json.tool > phase1_results/gamma_only/timelines.json

# Export to files
curl -X POST http://localhost:8000/options/export-timelines
```

### **Via Script (After Simulation)**

```python
from scripts.export_hedge_timelines import export_timelines_from_live_loop
from pathlib import Path

# Get live loop from bot_manager
export_timelines_from_live_loop(
    bot_manager.live_loop,
    Path("phase1_results/gamma_only")
)
```

### **Manual Export**

```python
# In Python after simulation
timeline_logger = bot_manager.live_loop.hedge_timeline_logger

for ml_pos in bot_manager.live_loop.options_portfolio.get_all_multi_leg_positions():
    timeline_table = timeline_logger.export_timeline_table(ml_pos.multi_leg_id)
    
    with open(f"phase1_results/gamma_only/{ml_pos.multi_leg_id}_timeline.txt", "w") as f:
        f.write(timeline_table)
    
    print(f"✅ Exported: {ml_pos.multi_leg_id}")
```

---

## Step 5: Review Timeline Tables

For each timeline table, check:

### **Delta Behavior**
- [ ] `OptDelta` moves with price as expected
- [ ] After hedge: `TotDelta` ≈ 0 (±0.05)
- [ ] Between hedges: `TotDelta` drifts but stays bounded

### **Hedge Trade Frequency**
- [ ] Hedge rows spaced out (respecting 5-bar frequency)
- [ ] No micro-hedges (< 5 shares)
- [ ] Hedge count ≤ 50 per day
- [ ] Notional < $100k per day

### **P&L Breakdown**
- [ ] On up-move: `options_pnl` positive, `hedge_pnl` negative, `total_pnl` net positive
- [ ] On round-trip: `total_pnl` positive (harvested gamma)
- [ ] At exit: `hedge_unrealized_pnl` ≈ 0, positions flat

### **Exit Reasons**
- [ ] Final row shows sensible exit reason (TP_150, SL_50, TIME_LIMIT, GEX_REVERSAL)
- [ ] P&L at exit matches trigger (e.g., TP=150% → total_pnl ≈ 150% of debit)

---

## Step 6: Validate Guardrails

### **Daily Limits**
- [ ] `hedge_trades_per_day` < 50
- [ ] `hedge_notional_per_day` < $100k
- [ ] Limits enforced correctly

### **Orphan Hedge Protection**
- [ ] If options close but hedge remains, auto-flatten after 60 bars
- [ ] Alert logged: `ORPHAN_HEDGE_FLATTEN`
- [ ] Hedge position removed correctly

---

## Step 7: Document Results

For each package tested:

1. **Save timeline table:**
   - `phase1_results/gamma_only/{multi_leg_id}_timeline.txt`

2. **Save metrics:**
   - `phase1_results/gamma_only/{multi_leg_id}_metrics.json`

3. **Update QA guide:**
   - Mark scenarios as PASSED in `GAMMA_SCALPER_QA_GUIDE.md`
   - Reference: `multi_leg_id`, date, file name

---

## Step 8: Proceed to Full Phase 1

Once Gamma-only test passes:

1. **Re-enable Theta Harvester:**
   ```python
   from scripts.create_all_options_agents import create_all_options_agents
   bot_manager.live_loop.agents = create_all_options_agents('SPY', ...)
   ```

2. **Run full Phase 1:**
   - Use existing Phase 1 test matrix
   - Run 3 historical periods
   - Execute Theta + Gamma scenarios
   - Score using `PHASE_1_EXIT_CRITERIA.md`

---

## Quick Reference

### **Start Test**
```bash
./START_VALIDATION.sh
```

### **Export Timelines**
```bash
curl -X POST http://localhost:8000/options/export-timelines
```

### **View Timelines**
```bash
curl http://localhost:8000/options/hedge-timelines | python3 -m json.tool
```

### **Check Logs**
```bash
tail -f logs/*.log | grep -i "gamma\|deltahedge\|multileg"
```

---

**Ready to run Gamma-only test!** 🚀

