# Trade Debugging Guide

## Problem: 0 Trades Despite 110,458 Bars Collected

### Root Cause Analysis

The issue is that preloaded bars were loaded into `bar_history` but **NOT processed through `_process_bar()`**, so:
- ✅ Bars were counted (`bars_per_symbol = 100`)
- ❌ Trading logic never executed
- ❌ No trades generated

### Fixes Applied

1. **Preload Processing Fix** (`core/live/scheduler.py`):
   - Preloaded bars are now processed through `_process_bar()` immediately
   - This triggers the full trading pipeline (regime, agents, trades)
   - Updates `bars_per_symbol` correctly during preload

2. **Diagnostic Logging** (`core/policy/controller.py`):
   - Added comprehensive logging for agent evaluation
   - Logs filter results
   - Logs arbitration decisions
   - Logs final intent details

### How to Debug

#### Step 1: Check Status
```bash
curl -s http://localhost:8000/live/status | python3 -m json.tool
```

Look for:
- `bars_per_symbol`: Should increase beyond 100
- `bar_count`: Should match total bars processed
- `is_running`: Should be `true` during simulation

#### Step 2: Check Logs in Settings Tab

1. Navigate to **Settings** tab
2. Filter logs by **INFO** and **Controller**
3. Look for these key messages:

**Agent Evaluation:**
```
🔍 [Controller] Collecting intents from X agents
🔍 [Controller] Agent trend_agent generated Y intents
  → Intent: LONG, confidence=0.XX, size=0.XXXX, reason=...
```

**Filtering:**
```
🔍 [Controller] Filtering X intents (testing_mode=true)
🔍 [Controller] After filtering: Y intents remain
⚠️ [Controller] All X intents were filtered out!  ← If this appears, filters are blocking
```

**Arbitration:**
```
🔍 [Controller] Arbitrating X scored intents
✅ [Controller] Final intent: delta=0.XXXX, confidence=0.XX, agent=trend_agent
```

**Trade Execution:**
```
✅ [TradeExecution] Executing trade: SPY, Delta=0.XXXX, Reason=...
```

### What Each Log Tells You

1. **"Agent X generated 0 intents"**
   - → Agent isn't generating signals
   - → Check agent logic (trend_agent, mean_reversion_agent, etc.)

2. **"All X intents were filtered out"**
   - → Filters are too strict
   - → Check filter logic in `core/policy/filters.py`
   - → Enable `testing_mode: true` to bypass filters

3. **"No scored intents"**
   - → Scoring failed
   - → Check scoring logic in `core/policy/scoring.py`

4. **"Final intent: delta=0.0000"**
   - → Intent has zero position delta
   - → Trade won't execute (no position change)

5. **"[TradeExecution] Executing trade" missing**
   - → Intent might be invalid
   - → Check `intent.is_valid` and `intent.position_delta`

### Expected Flow

1. Bar arrives → `_process_bar()` called
2. Features computed → Regime classified
3. Agents evaluated → Intents generated
4. Intents filtered → Valid intents remain
5. Intents scored → Best intent selected
6. Intent arbitrated → Final intent created
7. Trade executed → Order submitted

### Quick Fixes

If no trades after restart:

1. **Enable testing_mode:**
   ```json
   {
     "testing_mode": true,
     "offline_mode": true,
     "broker_type": "cached"
   }
   ```

2. **Check agent evaluation:**
   - Look for "Agent X generated Y intents" in logs
   - If all show 0 → agents need fixing

3. **Check filters:**
   - Look for "All X intents were filtered out"
   - If this appears → filters are blocking

4. **Check execution:**
   - Look for "[TradeExecution] Executing trade"
   - If missing → intent might be invalid

### Next Steps

1. Restart server
2. Start simulation with `testing_mode: true`
3. Check logs in Settings tab
4. Share log output showing:
   - Agent intents generated
   - Filter results
   - Final intent
   - Trade execution (if any)

This will pinpoint exactly where trades are being blocked! 🎯
