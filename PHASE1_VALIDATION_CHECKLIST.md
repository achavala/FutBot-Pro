# Phase 1 Validation Checklist

## ✅ Step 1: Clean Restart

### 1.1 Check for old processes
```bash
ps aux | grep uvicorn
kill <pid>  # for any leftover server
```

### 1.2 Start the API
```bash
python main.py --mode api --port 8000
# OR
uvicorn ui.fastapi_app:app --host 0.0.0.0 --port 8000 --reload
```

### 1.3 Sanity check
```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8000/live/status | python3 -m json.tool
```

**Expected:**
- `mode`: `backtest` or `offline`
- `is_running`: `false`
- no `error` / `stop_reason`

---

## ✅ Step 2: Run Small Offline Simulation

### 2.1 Start simulation
```bash
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["SPY"],
    "broker_type": "cached",
    "offline_mode": true,
    "testing_mode": true,
    "replay_speed": 600.0,
    "start_time": "2025-11-26T09:30:00",
    "end_time": "2025-11-26T10:00:00",
    "fixed_investment_amount": 10000.0
  }'
```

### 2.2 Check status after a few seconds
```bash
sleep 3
curl -s http://localhost:8000/live/status | python3 -m json.tool
```

**Healthy behavior:**
- ✅ `is_running` should flip to `false` after a few seconds
- ✅ `bars_per_symbol.SPY` ≈ number of bars in that 30-minute window (~30 bars)
- ✅ `stop_reason` should be `"completed"` or `"end_of_data"` or `"end_time_reached"`
- ✅ `error` should be `null`

**If `is_running` stays `true` for a long time** → we still have a loop/exception path to hunt.

---

## ✅ Step 3: Check Logs For Exceptions & Intents

### 3.1 Check for exceptions
```bash
tail -n 200 /tmp/futbot_server.log \
  | egrep "\[Controller\]|\[TradeExecution\]|intent|Exception|Traceback"
```

**You want to see:**
- ✅ Lines like:
  - `Agent trend_agent generated X intents`
  - `intents collected: N`
  - `After filtering: M scored intents`
  - `Final decision: direction=..., size=...`
- ✅ And **NO**:
  - `AttributeError: 'str' object has no attribute 'value'`
  - or any other unhandled Traceback

**Because you added "hard-fail if all agents blow up,"** if anything goes badly now, you should see a clear top-level error and the run should stop instead of hanging.

### 3.2 Count AttributeErrors
```bash
tail -n 300 /tmp/futbot_server.log | grep -c "AttributeError\|'str' object has no attribute 'value'" || echo "0"
```

**Expected:** `0` (no AttributeErrors)

---

## ✅ Step 4: Verify Trades are Actually Logged

### 4.1 Check trade log
```bash
curl -s http://localhost:8000/trade-log | python3 -m json.tool | head -50
```

**Expected:**
```json
{
  "trades": [
    {
      "symbol": "SPY",
      "entry_time": "...",
      "exit_time": "...",
      "entry_price": 455.23,
      "exit_price": 456.12,
      "quantity": 12,
      "pnl": 10.68,
      "pnl_pct": 0.19,
      "reason": "...",
      "agent": "trend_agent"
    },
    ...
  ],
  "total_count": N
}
```

**If `trades` is still `[]`:**
- Check logs for "No scored intents" (maybe filters are too strict / confidence too high)
- That would be a *logic* / configuration issue now, not a crash

---

## ✅ Step 5: Visual + Metrics Validation

### 5.1 Equity & Drawdown
```bash
curl -s http://localhost:8000/visualizations/equity-curve
curl -s http://localhost:8000/visualizations/drawdown
```
Should show something **non-flat** if trades happened.

### 5.2 Agent behavior
```bash
curl -s http://localhost:8000/visualizations/agent-fitness
curl -s http://localhost:8000/visualizations/weight-evolution
```

### 5.3 Metrics
```bash
curl -s http://localhost:8000/metrics | head -40
```

**Look for:**
- `futbot_trades_total`
- `futbot_pnl_cumulative`
- `futbot_risk_events_total`

This confirms that your **whole pipeline is now firing**: agents → controller → executor → portfolio → reward → adaptation → dashboards.

---

## 📊 Validation Results Template

After running all checks, document results:

```markdown
### Step 1: Clean Restart
- [ ] Server started successfully
- [ ] Health check passed
- [ ] Status shows clean state

### Step 2: Simulation Run
- [ ] Simulation started
- [ ] Completed in < 5 seconds
- [ ] `is_running`: false
- [ ] `bars_per_symbol.SPY`: ~30
- [ ] `stop_reason`: "completed" or "end_of_data"
- [ ] `error`: null

### Step 3: Logs Check
- [ ] No AttributeError exceptions
- [ ] Agent intents generated
- [ ] Controller processed intents
- [ ] No unhandled exceptions

### Step 4: Trades Verification
- [ ] Trades logged in `/trade-log`
- [ ] Trade count > 0
- [ ] Trade data complete

### Step 5: Metrics
- [ ] Equity curve non-flat
- [ ] Metrics show trades
- [ ] Agent fitness data available
```

---

## 🎯 Success Criteria

**Phase 1 is VALIDATED if:**
1. ✅ Simulation completes in < 5 seconds (30-minute replay at 600x)
2. ✅ No AttributeError exceptions in logs
3. ✅ Agent intents are generated and logged
4. ✅ Trades are executed and stored
5. ✅ Loop terminates cleanly with proper stop_reason

**If any check fails:**
- Document the failure
- Check logs for root cause
- Apply additional fixes as needed

---

## 🔜 Next Steps After Validation

Assuming all checks pass:

1. **Lock Phase 1 as "Green"** in STATUS / PHASE1 docs
2. **Add regression tests** for:
   - Logging trade intents without `.value` crashes
   - Controller raising on all-agents-error
3. **Run longer offline replay** (full day) in testing_mode
4. **Ready for Phase 2: ML Regime Engine** or multi-day paper burn-in


