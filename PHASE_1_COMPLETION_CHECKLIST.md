# Phase 1: Core Trading - Completion Checklist

## Goal: Get Trades Executing Reliably

### ✅ Completed

1. ✅ Bar processing pipeline
   - `_process_bar()` processes bars correctly
   - Preloaded bars go through trading pipeline
   - `bars_per_symbol` updates correctly

2. ✅ Strategy connection
   - Agents evaluate signals
   - Controller arbitrates intents
   - Filters apply correctly

3. ✅ Trade execution logic
   - Execution code in `_process_bar()`
   - Portfolio updates
   - Trade storage (`trade_history`)

4. ✅ API endpoints
   - `/live/status` returns complete status
   - `/trade-log` endpoint exists
   - Dashboard integration ready

### ⚠️ Needs Verification

1. ⚠️ Agent signal generation
   - Need to see logs showing agents generating intents
   - Check: Settings → Log Viewer → Filter "Controller"

2. ⚠️ Trade execution
   - Need to see "[TradeExecution] Executing trade" in logs
   - Check: Settings → Log Viewer → Filter "TradeExecution"

3. ⚠️ Trade storage
   - Need to verify trades appear in `/trade-log`
   - Check: `curl -s http://localhost:8000/trade-log | python3 -m json.tool`

4. ⚠️ UI display
   - Need to verify trades appear in Dashboard → Trades tab
   - Check: Dashboard → "Positions & Recent Trades" section

### 🔍 Verification Steps

1. **Start Simulation:**
   ```bash
   curl -X POST http://localhost:8000/live/start \
     -H "Content-Type: application/json" \
     -d '{
       "symbols": ["SPY", "QQQ"],
       "broker_type": "cached",
       "offline_mode": true,
       "testing_mode": true,
       "replay_speed": 600.0,
       "start_time": "2025-11-26T09:30:00",
       "end_time": "2025-11-26T16:00:00",
       "fixed_investment_amount": 10000.0
     }'
   ```

2. **Check Status:**
   ```bash
   curl -s http://localhost:8000/live/status | python3 -m json.tool
   ```
   - Should show `is_running: true`
   - Should show `bars_per_symbol` increasing

3. **Check Logs (Dashboard):**
   - Go to Settings → Log Viewer
   - Filter by "INFO" and "Controller"
   - Look for:
     * "Agent X generated Y intents"
     * "After filtering: X intents remain"
     * "Final intent: delta=..."
     * "[TradeExecution] Executing trade"

4. **Check Trades:**
   ```bash
   curl -s http://localhost:8000/trade-log | python3 -m json.tool
   ```
   - Should show trades if any executed

5. **Check Dashboard:**
   - Dashboard → Trades tab
   - "Positions & Recent Trades" section
   - Should show trades if any executed

### 🎯 Success Criteria

Phase 1 is complete when:
- ✅ Bars are processed (`bars_per_symbol` increases)
- ✅ Agents generate intents (visible in logs)
- ✅ Trades execute (visible in logs)
- ✅ Trades appear in `/trade-log` endpoint
- ✅ Trades appear in Dashboard UI

Once all criteria met → Proceed to Phase 2 (ML Regime Engine)

