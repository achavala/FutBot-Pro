# System Validation Checklist

## ✅ Step 1: Validate Date/Time Dropdown (REAL DATA ONLY)

### Test A: Dropdown Content
- [ ] Open dashboard and check date/time dropdown
- [ ] Verify dropdown shows ONLY cached dates
- [ ] Verify no future dates appear (e.g., Dec 1 when it's Nov 30)
- [ ] Verify no weekends/holidays appear
- [ ] Verify only market hours (9:30 AM - 4:00 PM)
- [ ] Verify dates are sorted (newest first)

### Test B: API Endpoint
```bash
# Test the endpoint directly
curl -s "http://localhost:8000/cache/available-dates?timeframe=1min" | python3 -m json.tool
```

**Expected:**
- Returns `available_dates` array with real dates
- Each date has `times` array with actual timestamps
- `total_dates` matches number of dates with cached data

### Test C: Simulation Start
- [ ] Pick any date from dropdown
- [ ] Click "Start" simulation
- [ ] Check logs for "Using cached data" messages
- [ ] Verify NO "SyntheticBarFallback" warnings (if strict_data_mode=True)
- [ ] Simulation should start immediately

---

## ✅ Step 2: Validate Trades & P&L (Stocks + Options)

### Test A: Stock Trades
```bash
# Get stock round-trip trades
curl -s "http://localhost:8000/trades/roundtrips?limit=10" | python3 -m json.tool
```

**Check:**
- [ ] Entry/exit prices match cached bar data
- [ ] P&L calculations are correct: `(exit_price - entry_price) * quantity`
- [ ] Timestamps match cached data (not synthetic)
- [ ] Quantities are realistic (not 0.00000)
- [ ] Prices match Webull (~$605 for QQQ, ~$475 for SPY on Nov 24)

### Test B: Options Trades
```bash
# Get options round-trip trades
curl -s "http://localhost:8000/trades/options/roundtrips?limit=10" | python3 -m json.tool
```

**Check:**
- [ ] Options trades appear (if options agent generated intents)
- [ ] Entry/exit premiums are reasonable ($1-20 range typically)
- [ ] P&L reflects underlying moves (magnified)
- [ ] Option type (CALL/PUT) matches market conditions
- [ ] Strike prices are reasonable (ATM ≈ underlying price)
- [ ] Regime/volatility metadata present

### Test C: Price Validation
- [ ] Compare entry prices with Webull at same timestamp
- [ ] Prices should match within $0.50 (accounting for bid/ask spread)
- [ ] No prices showing $100 or other default values

---

## ✅ Step 3: Validate Frontend Simulation Status & Progress

### Test A: Start Simulation
- [ ] Select date/time from dropdown
- [ ] Click "Start" button
- [ ] Check Status tab immediately

**Expected:**
- [ ] Progress bar appears and updates
- [ ] Sparkline throughput graph shows bars/second
- [ ] "Simulating - Running" status (green)
- [ ] Bar count increases
- [ ] Last bar time updates

### Test B: During Simulation
- [ ] Watch progress bar go 0% → 100%
- [ ] Throughput sparkline updates in real-time
- [ ] Summary stats box shows:
  - Total trades count
  - Winning/losing trades
  - P&L
  - Max drawdown
- [ ] Last trade snapshot updates when trades occur

### Test C: Completion
- [ ] Simulation completes without freezing
- [ ] Status changes to "Simulation Completed" or "end_of_data"
- [ ] Progress bar reaches 100%
- [ ] Final stats are displayed
- [ ] No error messages

---

## ✅ Step 4: Validate Options Trades in UI

### Test A: Options Agent Generation
- [ ] Run simulation with bullish conditions (QQQ trending up)
- [ ] Check logs for "OptionsAgent" messages
- [ ] Verify CALL intents are generated

- [ ] Run simulation with bearish conditions
- [ ] Verify PUT intents are generated

### Test B: Options Trades API
```bash
# Check if options trades exist
curl -s "http://localhost:8000/trades/options/roundtrips" | python3 -m json.tool | head -50
```

**Expected:**
- [ ] Options trades appear in response
- [ ] Each trade has:
  - `option_type`: "call" or "put"
  - `strike`: Strike price
  - `entry_price` / `exit_price`: Premiums
  - `gross_pnl`: P&L in dollars
  - `regime_at_entry` / `vol_bucket_at_entry`: Metadata

### Test C: Options Dashboard (Already Implemented!)
- [ ] Navigate to Analytics → Options Dashboard tab
- [ ] Verify 4 visualizations appear:
  - [ ] Options Equity Curve
  - [ ] Options Drawdown
  - [ ] Options P&L by Symbol
  - [ ] Options vs Stock Comparison
- [ ] Charts should update when options trades exist

---

## ✅ Step 5: Options Dashboard Integration (ALREADY COMPLETE!)

✅ **Status: IMPLEMENTED**

The Options Dashboard was already implemented in the previous session:
- ✅ Options metrics tracking in BotManager
- ✅ 4 visualization functions in `visualizations.py`
- ✅ 4 FastAPI endpoints
- ✅ Frontend UI in Analytics tab

**Validation:**
- [ ] Navigate to Analytics → Options Dashboard
- [ ] All 4 charts should render
- [ ] Charts show data when options trades exist
- [ ] Placeholders show when no options trades

---

## ✅ Step 6: Multi-Day Backtest Benchmark

### Test A: 5-Day Backtest
```bash
# Start 5-day simulation
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["SPY", "QQQ"],
    "broker_type": "cached",
    "offline_mode": true,
    "testing_mode": true,
    "strict_data_mode": true,
    "replay_speed": 3000.0,
    "start_time": "2025-11-20T09:30:00",
    "end_time": "2025-11-24T16:00:00",
    "fixed_investment_amount": 10000.0
  }'
```

**Check:**
- [ ] Completes in reasonable time (5-15 seconds)
- [ ] No exceptions in logs
- [ ] Both stock and options trades execute
- [ ] Performance metrics are reasonable
- [ ] No memory leaks or slowdowns

### Test B: 30-Day Backtest
```bash
# Start 30-day simulation (adjust dates based on available cache)
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["SPY", "QQQ"],
    "broker_type": "cached",
    "offline_mode": true,
    "testing_mode": true,
    "strict_data_mode": true,
    "replay_speed": 5000.0,
    "start_time": "2025-10-01T09:30:00",
    "end_time": "2025-10-31T16:00:00",
    "fixed_investment_amount": 10000.0
  }'
```

**Check:**
- [ ] Completes successfully
- [ ] Performance is acceptable (30-60 seconds for 30 days)
- [ ] All trades are logged correctly
- [ ] Equity curve is smooth (no sudden jumps)
- [ ] Regime transitions are handled correctly

### Test C: Performance Metrics
- [ ] Check processing speed: Should be 100-700 bars/second
- [ ] Check memory usage: Should be stable
- [ ] Check CPU usage: Should be reasonable
- [ ] No crashes or freezes

---

## ✅ Step 7: System Health Check

### Test A: Logs
```bash
# Check for errors
tail -n 200 /tmp/futbot_server.log | grep -i "error\|exception\|traceback"
```

**Expected:**
- [ ] No critical errors
- [ ] No unhandled exceptions
- [ ] No "SyntheticBarFallback" (if strict mode enabled)

### Test B: API Health
```bash
# Check all endpoints
curl -s http://localhost:8000/health
curl -s http://localhost:8000/live/status | python3 -m json.tool
curl -s http://localhost:8000/stats | python3 -m json.tool
```

**Expected:**
- [ ] All endpoints return valid JSON
- [ ] No 500 errors
- [ ] Status reflects current state correctly

### Test C: Cache Integrity
```bash
# Check cache contents
sqlite3 data/cache.db "SELECT symbol, COUNT(*) as count, MIN(ts) as first_ts, MAX(ts) as last_ts FROM polygon_bars WHERE timeframe='1min' GROUP BY symbol;"
```

**Expected:**
- [ ] Cache has data for SPY and QQQ
- [ ] Timestamps are in milliseconds
- [ ] Date ranges are reasonable (not future dates)

---

## 🎯 Quick Validation Script

Run this to quickly check system health:

```bash
#!/bin/bash
echo "=== System Validation ==="
echo ""
echo "1. API Health:"
curl -s http://localhost:8000/health | python3 -m json.tool
echo ""
echo "2. Available Cached Dates:"
curl -s "http://localhost:8000/cache/available-dates?timeframe=1min" | python3 -m json.tool | head -20
echo ""
echo "3. Stock Trades (last 5):"
curl -s "http://localhost:8000/trades/roundtrips?limit=5" | python3 -m json.tool
echo ""
echo "4. Options Trades (last 5):"
curl -s "http://localhost:8000/trades/options/roundtrips?limit=5" | python3 -m json.tool
echo ""
echo "5. System Status:"
curl -s http://localhost:8000/live/status | python3 -m json.tool | grep -E "is_running|mode|bars_per_symbol"
```

---

## 📋 Summary

Once all checks pass:
- ✅ System is using REAL cached data only
- ✅ Trades are executing correctly
- ✅ P&L is accurate
- ✅ Options trading is working
- ✅ Dashboard visualizations are functional
- ✅ System is ready for multi-day backtests
- ✅ Ready for Phase 2: ML Regime Engine
