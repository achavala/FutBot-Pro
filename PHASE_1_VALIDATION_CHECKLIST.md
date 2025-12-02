# Phase 1: Simulation Validation Checklist

**Version:** 2.0 (Production-Ready)  
**Last Updated:** 2024-12-01  
**Status:** Ready for Execution

---

## 🎯 **Phase 1 Exit Criteria**

**Phase 1 PASSES when ALL of the following are true:**

- ✅ **No P&L Mismatches:**
  - Package P&L = Sum of leg P&L (within $0.01 tolerance)
  - UI P&L = API P&L = Database P&L (within $0.01 tolerance)
  - Log P&L matches calculated P&L

- ✅ **All Auto-Exit Triggers Fire Correctly:**
  - Theta Harvester TP (50%) fires in at least 2 trend-up days
  - Theta Harvester SL (200%) fires in at least 1 fast-dump day
  - Theta Harvester IV collapse fires in at least 1 IV-drop day
  - Theta Harvester regime change fires in at least 1 compression→expansion day
  - Gamma Scalper TP (150%) fires in at least 2 big-move days
  - Gamma Scalper SL (50%) fires in at least 1 whipsaw day
  - Gamma Scalper GEX reversal fires in at least 1 GEX-flip day
  - Time-limit exits fire correctly

- ✅ **No Orphaned Legs or Stuck Packages:**
  - All multi-leg positions either close or remain open with valid reason
  - No positions stuck in "pending" state indefinitely
  - All exit orders execute successfully

- ✅ **Zero Unhandled Exceptions:**
  - No exceptions in logs over N days of simulation (N ≥ 3)
  - All errors are caught and logged with context
  - System continues running after errors

- ✅ **Deterministic Logging:**
  - Every package traceable by `multi_leg_id`
  - Entry/exit timestamps logged
  - Leg order IDs logged
  - Exit reasons logged

**If ALL criteria pass → Proceed to Phase 2 (Paper Live)**

---

## 📋 **Pre-Flight Checks**

### ✅ **1. Environment Sanity**

#### **1.1 Configuration**
- [ ] **SIM/PAPER Flag:** Verify `offline_mode=True` or `testing_mode=True` in config
- [ ] **Database:** Using dedicated test DB or cleared state
- [ ] **Logging Level:** Set to `DEBUG` for:
  - `core.live.executor_options`
  - `core.live.multi_leg_profit_manager`
  - `core.agents.theta_harvester`
  - `core.agents.gamma_scalper`
- [ ] **Time Source:** Locked to simulation time (no timezone weirdness)
- [ ] **Data Source:** Cached historical data available for test periods

#### **1.1.1 Config Snapshot (NEW)**
- [ ] **Dump Effective Config:** At startup, dump effective config to `run_config.json`:
  ```json
  {
    "run_id": "run_20241201_143022",
    "git_commit": "abc123...",
    "git_tag": "v1.0.0-ml-multi-leg",
    "timestamp": "2024-12-01T14:30:22Z",
    "broker_mode": "SIM",
    "strategy_params": {
      "theta_harvester": {
        "take_profit_pct": 50.0,
        "stop_loss_pct": 200.0,
        "iv_collapse_threshold": 0.3,
        "exit_on_regime_change": true
      },
      "gamma_scalper": {
        "take_profit_pct": 150.0,
        "stop_loss_pct": 50.0,
        "gex_reversal_threshold": 1.0,
        "min_hold_bars": 5,
        "max_hold_bars": 390
      }
    },
    "symbols_universe": ["SPY", "QQQ"],
    "test_periods": [
      {"name": "trending_up", "start": "2024-12-01", "end": "2024-12-05"},
      {"name": "trending_down", "start": "2024-11-15", "end": "2024-11-20"},
      {"name": "choppy", "start": "2024-11-25", "end": "2024-11-30"}
    ]
  }
  ```
- [ ] **Verify Config File:** `run_config.json` exists and contains all parameters
- [ ] **Archive Config:** Save config with run results for audit trail

#### **1.1.2 Determinism Seed (NEW)**
- [ ] **Set Random Seeds:** Log/set at startup:
  ```python
  RANDOM_SEED = 42  # Logged
  PYTHONHASHSEED = 42  # Set in environment
  numpy.random.seed(42)  # Set
  torch.manual_seed(42)  # If using PyTorch
  ```
- [ ] **Log Seeds:** All seeds logged to `run_config.json`
- [ ] **Verify Reproducibility:** Same seed + same data = same results

#### **1.1.3 Version Stamp (NEW)**
- [ ] **Log Version Info:** At startup, log to `run_config.json`:
  - Git commit hash: `git rev-parse HEAD`
  - Git tag: `v1.0.0-ml-multi-leg`
  - Python version: `python --version`
  - Key dependencies:
    - `pandas.__version__`
    - `numpy.__version__`
    - Broker SDK version (Alpaca, IBKR, etc.)
- [ ] **Verify Version Logged:** Check `run_config.json` contains all versions

#### **1.2 System Status**
- [x] Multi-leg execution implemented
- [x] Auto-exit logic complete
- [x] UI integration done
- [x] API endpoints working
- [x] Unit tests passing

#### **1.3 Clean Restart**
```bash
# Kill any existing processes
pkill -f uvicorn
pkill -f "python.*main.py"

# Clear port
lsof -ti:8000 | xargs kill -9 2>/dev/null

# Start fresh
cd /Users/chavala/FutBot
python main.py --mode api --port 8000
```

#### **1.4 Dashboard Access**
- Open: `http://localhost:8000/dashboard`
- Verify: System shows "Stopped" initially
- Check: Browser console has no errors

---

## 🧪 **Test Matrix: Historical Periods**

**IMPORTANT:** Use actual date ranges for THIS run. Document exact periods tested.

### **Period 1: Trending Up**
**Dates:** SPY / QQQ during **YYYY-MM-DD → YYYY-MM-DD** (e.g., 2024-12-01 → 2024-12-05)
**Expected Behavior:**
- Theta Harvester: Should hit TP (50%) on profitable days
- Gamma Scalper: Should hit TP (150%) on big moves
**Verification:**
- [ ] At least 2 TP triggers fire for Theta Harvester
- [ ] At least 2 TP triggers fire for Gamma Scalper

### **Period 2: Trending Down**
**Dates:** SPY / QQQ during **YYYY-MM-DD → YYYY-MM-DD** (e.g., 2024-11-15 → 2024-11-20)
**Expected Behavior:**
- Theta Harvester: Should hit SL (200%) on fast dumps
- Gamma Scalper: Should hit TP on downward moves
**Verification:**
- [ ] At least 1 SL trigger fires for Theta Harvester
- [ ] At least 1 TP trigger fires for Gamma Scalper

### **Period 3: Choppy/Compressed**
**Dates:** SPY / QQQ during **YYYY-MM-DD → YYYY-MM-DD** (e.g., 2024-11-25 → 2024-11-30)
**Expected Behavior:**
- Theta Harvester: Should enter in compression, exit on regime change
- Gamma Scalper: Should enter on negative GEX, exit on reversal
**Verification:**
- [ ] At least 1 regime change exit fires for Theta Harvester
- [ ] At least 1 GEX reversal exit fires for Gamma Scalper

### **Period 4: Major Event (NEW)**
**Dates:** SPY / QQQ during **YYYY-MM-DD → YYYY-MM-DD** (e.g., FOMC meeting week, CPI release week)
**Event:** FOMC / CPI / Major earnings
**Expected Behavior:**
- Regime flips during event
- IV spikes/collapses
- GEX changes dramatically
**Verification:**
- [ ] Regime change detected and logged
- [ ] IV collapse exits fire if applicable
- [ ] GEX reversal exits fire if applicable

### **Period 5: Options Expiry Week (NEW)**
**Dates:** SPY / QQQ during **YYYY-MM-DD → YYYY-MM-DD** (e.g., Third Friday week)
**Expected Behavior:**
- Time decay accelerates near expiry
- Gamma effects more pronounced
- Early exits may trigger
**Verification:**
- [ ] Time-based exits fire correctly
- [ ] No positions held past expiry
- [ ] P&L calculations correct with time decay

---

## 📊 **Scenario Tests**

### **A. Theta Harvester (Straddle Seller) Scenarios**

#### **A1. Normal Green Day → TP at +50%**
**Entry Conditions:**
- Symbol: SPY
- Regime: Compression
- IV Percentile: >70th percentile
- Entry: Sell ATM straddle, DTE=3-7 days
- Expected Credit: ~$X.XX per contract

**Expected Exit Condition:**
- Close package when net P&L >= +50% of initial credit
- Pass if: Exit occurs between +48% and +52% P&L
- Exit reason logged as: `"Theta Harvester TP: 50.0% profit"`

**Verification:**
- [ ] Position created with both legs filled
- [ ] Credit received matches expected (±10% tolerance)
- [ ] P&L updates in real-time
- [ ] TP triggers at 50% profit (±2% tolerance)
- [ ] Both legs close simultaneously
- [ ] Trade record created with correct P&L
- [ ] Exit reason matches expected format

**Log Pattern:**
```
[THETA HARVEST] Compression + IV=75.2% → SELL 3x ATM straddle @ $673.00
[MultiLeg] Executing SHORT STRADDLE 3x: CALL $673.00 @ $2.50 + PUT $673.00 @ $2.30
[MultiLeg] CALL fill: 3 @ $2.50 (status: filled)
[MultiLeg] PUT fill: 3 @ $2.30 (status: filled)
[MultiLeg] STRADDLE position created: SPY_STRADDLE_short_673_673_20241126
[MultiLeg] Expected credit: $1,440.00
[MultiLeg] Actual credit: $1,440.00 ✅
[MultiLegExit] Closing STRADDLE SPY_STRADDLE_short_673_673_20241126: Theta Harvester TP: 50.0% profit
[MultiLeg] STRADDLE closed: Combined P&L: $720.00 (50.0%)
```

#### **A2. Fast Dump → SL at -200%**
**Setup:**
- Compression regime + High IV
- Straddle sold, then price moves rapidly against position

**Expected:**
- [ ] Position created
- [ ] P&L goes negative
- [ ] SL triggers at -200% of credit
- [ ] Both legs close
- [ ] Trade record shows loss

**Log Pattern:**
```
[MultiLegExit] Closing STRADDLE: Theta Harvester SL: -200.0% loss (limit: 200%)
[MultiLeg] STRADDLE closed: Combined P&L: -$2,880.00 (-200.0%)
```

#### **A3. IV Collapse While Price Drifts → Exit on IV Rule**
**Setup:**
- Straddle sold in high IV environment
- IV drops 30%+ while price stays range-bound

**Expected:**
- [ ] Position created
- [ ] IV monitored continuously
- [ ] IV collapse detected (30%+ drop)
- [ ] Exit triggered with reason "IV collapse"
- [ ] Trade profitable (IV decay)

**Log Pattern:**
```
[MultiLegExit] Closing STRADDLE: Theta Harvester IV collapse: IV dropped 35.2% (0.45 → 0.29)
```

#### **A4. Regime Change Mid-Trade → Exit on Regime**
**Setup:**
- Straddle sold in compression regime
- Regime changes to expansion/trend

**Expected:**
- [ ] Position created in compression
- [ ] Regime change detected
- [ ] Exit triggered with reason "regime change"
- [ ] Trade record includes regime transition

**Log Pattern:**
```
[MultiLegExit] Closing STRADDLE: Theta Harvester regime exit: compression ended (now: expansion)
```

---

### **B. Gamma Scalper (Strangle Buyer) Scenarios**

#### **B1. Big Move → +150% TP Hit**
**Setup:**
- Negative GEX + Cheap IV (<30th percentile)
- Strangle bought (OTM call + OTM put)
- Price moves significantly

**Expected:**
- [ ] Position created with both legs filled
- [ ] Debit paid matches expected (±10% tolerance)
- [ ] P&L updates in real-time
- [ ] TP triggers at 150% gain
- [ ] Both legs close simultaneously
- [ ] Trade record created with correct P&L

**Log Pattern:**
```
[GAMMA SCALP] NEGATIVE GEX (-2.5B) + IV=25.3% → BUY 2x 25Δ strangle
[MultiLeg] Executing LONG STRANGLE 2x: CALL $680.00 @ $1.20 + PUT $665.00 @ $1.10
[MultiLeg] CALL fill: 2 @ $1.20 (status: filled)
[MultiLeg] PUT fill: 2 @ $1.10 (status: filled)
[MultiLeg] STRANGLE position created: SPY_STRANGLE_long_680_665_20241126
[MultiLegExit] Closing STRANGLE: Gamma Scalper TP: 150.0% profit (target: 150%)
[MultiLeg] STRANGLE closed: Combined P&L: $690.00 (150.0%)
```

#### **B2. Whipsaw → -50% SL Hit**
**Setup:**
- Strangle bought
- Price whipsaws without directional move

**Expected:**
- [ ] Position created
- [ ] P&L goes negative
- [ ] SL triggers at -50% loss
- [ ] Both legs close
- [ ] Trade record shows loss

**Log Pattern:**
```
[MultiLegExit] Closing STRANGLE: Gamma Scalper SL: -50.0% loss (limit: 50%)
```

#### **B3. GEX Reversal → Exit on GEX Rule**
**Setup:**
- Strangle bought on negative GEX
- GEX flips to positive (>threshold)

**Expected:**
- [ ] Position created with negative GEX entry
- [ ] GEX monitored continuously
- [ ] GEX reversal detected
- [ ] Exit triggered with reason "GEX reversal"
- [ ] Trade record includes GEX transition

**Log Pattern:**
```
[MultiLegExit] Closing STRANGLE: Gamma Scalper GEX reversal: GEX flipped from negative (-2.5B) to positive (1.2B)
```

#### **B4. Time-Limit Exit (No TP/SL) → Exit at EOD**
**Setup:**
- Strangle bought
- No TP/SL hit, but max hold time reached

**Expected:**
- [ ] Position created
- [ ] Time tracked (bars held)
- [ ] Max hold time reached (390 bars)
- [ ] Exit triggered with reason "maximum hold time"
- [ ] Trade record includes duration

**Log Pattern:**
```
[MultiLegExit] Closing STRANGLE: Maximum hold time reached (390 bars)
```

---

### **C. Gamma Scalper Delta Hedging Scenarios**

#### **C1. Clean Up-Move with Re-Hedges (G-H1)**
**Setup:**
- Gamma Scalper buys long strangle (near ATM, delta ≈ 0)
- Underlying grinds up steadily

**Expected:**
- [ ] Options delta becomes positive as price rises
- [ ] Hedge trades execute: sell shares to neutralize delta
- [ ] Total delta stays around 0 over the path
- [ ] Number of hedge trades is reasonable (not firing every tick)
- [ ] `current_hedge_shares` evolution makes sense (increasing short as price rises)
- [ ] Total P&L = options gamma gains - hedge losses (net positive in good vol)

**Verification:**
- [ ] Net delta calculated correctly: `(call_delta * call_qty) + (put_delta * put_qty)`
- [ ] Hedge quantity calculated correctly: `hedge_shares = -net_delta * 100`
- [ ] Hedge adjusts from current position (not resetting)
- [ ] Hedge P&L tracked separately (realized + unrealized)
- [ ] Combined P&L = options_pnl + hedge_pnl

**Log Pattern:**
```
[DeltaHedge] SPY_STRANGLE_long_680_665_20241126: Hedging SELL 25.00 shares @ $673.50 (net_delta=+0.25, current_hedge=0.00)
[DeltaHedge] Updated hedge position: 0.00 → -25.00 shares @ avg $673.50
[DeltaHedge] SPY_STRANGLE_long_680_665_20241126: Hedge P&L=$-12.50 (unrealized)
```

#### **C2. Down-Move / Round-Trip (G-H2)**
**Setup:**
- Gamma Scalper buys long strangle
- Underlying moves up then back down over the same day

**Expected:**
- [ ] Delta neutralized on up-move (short shares)
- [ ] Delta neutralized on down-move (long shares)
- [ ] End roughly flat delta and flat hedge shares
- [ ] Net total_pnl should be positive in decent vol path
- [ ] No leftover hedge when options are closed
- [ ] `hedge_realized_pnl + options_realized_pnl` matches total

**Verification:**
- [ ] Hedge position flattens correctly on exit
- [ ] Final hedge P&L realized correctly
- [ ] Combined P&L calculation accurate

#### **C3. No Hedge Band / Frequency Limit (G-H3)**
**Setup:**
- Underlying shows oscillating moves around the strike
- Delta crosses threshold and comes back quickly

**Expected:**
- [ ] Frequency limit (5 bars) is respected
- [ ] No micro-hedges (< 5 shares)
- [ ] Don't hammer broker with excessive trades
- [ ] Delta threshold (0.10) prevents over-trading

**Verification:**
- [ ] Hedge count reasonable for period
- [ ] Minimum hedge size enforced (5 shares)
- [ ] Frequency limit prevents over-trading

#### **C4. Engine Restart Mid-Hedged (G-H4)**
**Setup:**
- Open Gamma Scalper package
- Nonzero hedge_shares on the symbol
- Restart engine

**Expected:**
- [ ] On reload, engine reconstructs:
  - Options position
  - Hedge position (shares, avg_price)
  - Correct net_delta and P&L
- [ ] Next hedge action is small adjustment, not overshoot
- [ ] Hedge P&L continues tracking correctly

**Verification:**
- [ ] State reloads correctly from database
- [ ] Hedge position reconstructed
- [ ] Average price maintained
- [ ] Next hedge is adjustment, not reset

---

## 🔍 **Edge Cases**

### **E1. Partial Fill on One Leg**
**Setup:**
- Multi-leg order submitted
- Call leg fills completely
- Put leg fills partially

**Expected:**
- [ ] Position created with `both_legs_filled=False`
- [ ] Call leg shows "filled" status
- [ ] Put leg shows "partially_filled" status
- [ ] Auto-exit does NOT trigger (waiting for full fill)
- [ ] Position remains in "Open Positions" table
- [ ] Log shows warning: "Position not fully filled yet"

**Verification:**
```bash
# Check API response
curl http://localhost:8000/options/positions | jq '.multi_leg_positions[] | select(.both_legs_filled == false)'
```

### **E2. One Leg Rejected**
**Setup:**
- Multi-leg order submitted
- Call leg fills
- Put leg rejected by broker

**Expected:**
- [ ] Position created with `both_legs_filled=False`
- [ ] Call leg shows "filled" status
- [ ] Put leg shows "rejected" status
- [ ] Position marked as "BROKEN" or "NEEDS_MANUAL_REVIEW"
- [ ] Auto-exit does NOT trigger
- [ ] Alert logged: "Multi-leg position broken - manual review needed"
- [ ] Position remains in "Open Positions" with warning indicator

**Verification:**
```bash
# Check logs for rejection
tail -f logs/*.log | grep -i "rejected\|broken\|manual"
```

### **E3. Network/API Error During Close**
**Setup:**
- Multi-leg position open
- Auto-exit triggered
- Network error occurs during closing order submission

**Expected:**
- [ ] Error caught and logged with context
- [ ] Retry logic attempts (with backoff)
- [ ] Position remains open if retry fails
- [ ] Alert logged: "Failed to close multi-leg position - retrying"
- [ ] System continues running (no crash)

**Verification:**
```bash
# Check logs for retry attempts
tail -f logs/*.log | grep -i "retry\|backoff\|failed to close"
```

### **E4. Multiple Packages Per Symbol**
**Setup:**
- Theta Harvester enters straddle on SPY
- Gamma Scalper enters strangle on SPY (different strikes)

**Expected:**
- [ ] Both positions created independently
- [ ] Each has unique `multi_leg_id`
- [ ] Both tracked separately
- [ ] Both appear in "Open Positions" table
- [ ] Auto-exit checks both independently
- [ ] No conflicts or interference

**Verification:**
```bash
# Check API for multiple positions
curl http://localhost:8000/options/positions | jq '.multi_leg_positions | length'
```

### **E5. Signal Flips Multiple Times**
**Setup:**
- Theta Harvester enters straddle
- Exits on TP
- Re-enters same day (conditions met again)

**Expected:**
- [ ] First position closes correctly
- [ ] Second position opens with new `multi_leg_id`
- [ ] Both trades recorded in history
- [ ] No duplicate IDs
- [ ] No state leakage between positions

### **E6. Engine Restart Mid-Trade (NEW)**
**Setup:**
- Multi-leg position open
- Kill and restart engine
- Position should still be tracked

**Expected:**
- [ ] State reloads correctly from database
- [ ] Open position appears in portfolio
- [ ] Auto-exit logic resumes correctly
- [ ] No double entry (position not duplicated)
- [ ] No lost exit (exit logic still works)
- [ ] P&L continues tracking correctly

**Verification:**
```bash
# 1. Start engine, enter position
# 2. Kill engine: pkill -f "python.*main.py"
# 3. Restart engine
# 4. Check: Position still tracked, auto-exit works
```

### **E7. Clock/Time Anomalies (NEW)**
**Setup:**
- Simulate clock drift OR DST change OR weekend gap
- Test time-based exits (timeouts, EOD exits)

**Expected:**
- [ ] No trades in closed markets (pre-market, after-hours, weekends)
- [ ] Time-based exits fire correctly (EOD, timeout)
- [ ] No duplicate bars on clock adjustments
- [ ] Timestamps remain consistent

**Verification:**
- [ ] Test with simulated DST change
- [ ] Test with weekend gap
- [ ] Test with market hours boundaries
- [ ] Verify time-based exits fire at correct times

---

## 🛡️ **Risk Limits Verification**

### **R1. Per-Strategy Max Margin/Notional**
**Check:**
- [ ] Theta Harvester: Max position size enforced
- [ ] Gamma Scalper: Max position size enforced
- [ ] Risk manager prevents over-sizing

**Verification:**
```bash
# Check logs for risk limit hits
tail -f logs/*.log | grep -i "risk limit\|max position\|margin"
```

### **R2. Max Open Packages**
**Check:**
- [ ] System enforces max open multi-leg positions
- [ ] New entries blocked when limit reached
- [ ] Log shows reason: "Max open packages reached"

### **R3. Daily Loss Limit**
**Check:**
- [ ] Per-strategy daily loss limit enforced
- [ ] Global daily loss limit enforced
- [ ] Hard stop when limit hit
- [ ] New entries disabled after limit

**Verification:**
```bash
# Check risk manager logs
tail -f logs/*.log | grep -i "daily loss\|circuit breaker"
```

### **R4. Behavior When Risk Limit Hit**
**Check:**
- [ ] **Stops New Entries:** When limit hit, engine stops new entries for that strategy only
- [ ] **Allows Exits:** Existing positions can still exit (risk-reducing actions allowed)
- [ ] **Logs Clear Event:** RISK_BLOCK event logged with:
  - Which limit (daily_loss, max_margin, max_packages)
  - Current values vs limit
  - Strategy affected
- [ ] **UI/API Shows State:** UI/API show visible state: "Strategy blocked by risk manager"
- [ ] **No Mystery:** Clear reason why trading stopped

**Log Pattern:**
```
[RISK_BLOCK] Theta Harvester blocked: Daily loss limit exceeded ($2,100.00 >= $2,000.00)
[RISK_BLOCK] Strategy: theta_harvester, Limit: daily_loss, Current: $2,100.00, Limit: $2,000.00
```

**Verification:**
```bash
# Check logs for RISK_BLOCK events
tail -f logs/*.log | grep -i "risk_block"

# Check API for blocked state
curl http://localhost:8000/live/status | jq '.risk_blocks'
```

---

## 🔄 **State Reconciliation**

### **S1. Package P&L vs Sum of Legs**
**Check:**
- [ ] For each open position:
  - Package P&L = Call P&L + Put P&L (within $0.01)
- [ ] For each closed trade:
  - Trade P&L = Sum of leg P&Ls (within $0.01)

**Verification:**
```python
# Run reconciliation script
python scripts/reconcile_multi_leg_pnl.py
```

### **S2. UI vs API vs Database**
**Check:**
- [ ] UI positions match API `/options/positions`
- [ ] API positions match database
- [ ] UI history matches API `/trades/options/multi-leg`
- [ ] API history matches database

**Verification:**
```bash
# Compare UI and API
curl http://localhost:8000/options/positions | jq '.multi_leg_positions' > api_positions.json
# Compare with UI table data
```

### **S3. Log vs Database**
**Check:**
- [ ] Every package in database has log entry
- [ ] Every log entry has database record
- [ ] Entry/exit times match (within 1 second)

### **S4. Reconciliation Script/Endpoint (NEW)**
**Check:**
- [ ] **Reconciliation Tool:** Script or endpoint `reconcile_positions` exists
- [ ] **Compares State:** Compares DB state vs computed from raw trades/logs
- [ ] **Produces Diff Report:** Short "diff report" generated
- [ ] **On Mismatch:**
  - Logs severity WARNING/ERROR
  - Attaches package_id, leg IDs, computed vs stored P&L
  - Adds to Phase 1 log/summary (not hidden)

**Verification:**
```bash
# Run reconciliation
python scripts/reconcile_multi_leg_positions.py

# Or via API
curl http://localhost:8000/options/reconcile | python3 -m json.tool

# Expected output:
# {
#   "status": "ok",
#   "total_positions": 10,
#   "mismatches": 0,
#   "diff_report": []
# }
```

---

## 📝 **Deterministic Logging**

### **D1. Package Traceability**
**Check:**
- [ ] Every package has unique `multi_leg_id`
- [ ] Format: `{symbol}_{trade_type}_{direction}_{call_strike}_{put_strike}_{expiration}`
- [ ] ID logged at entry and exit

### **D2. Timestamps**
**Check:**
- [ ] Entry timestamp logged: `entry_time`
- [ ] Exit timestamp logged: `exit_time`
- [ ] Timestamps in ISO format
- [ ] Timezone consistent

### **D3. Leg Order IDs**
**Check:**
- [ ] Call leg order ID logged
- [ ] Put leg order ID logged
- [ ] Exit order IDs logged
- [ ] Order IDs match broker records (if applicable)

### **D4. Exit Reasons**
**Check:**
- [ ] Every exit has reason logged:
  - `"Theta Harvester TP: 50.0% profit"`
  - `"Theta Harvester SL: -200.0% loss"`
  - `"Theta Harvester IV collapse: ..."`
  - `"Theta Harvester regime exit: ..."`
  - `"Gamma Scalper TP: 150.0% profit"`
  - `"Gamma Scalper SL: -50.0% loss"`
  - `"Gamma Scalper GEX reversal: ..."`
  - `"Maximum hold time reached"`
- [ ] Reason included in trade record

### **D5. Correlation ID (NEW)**
**Check:**
- [ ] **Single Correlation ID:** Each simulation run has unique `run_id`
- [ ] **Per Package Logging:** For each package, log:
  - `run_id` (e.g., "run_20241201_143022")
  - `package_id` (multi_leg_id)
  - `strategy_name` (theta_harvester, gamma_scalper)
  - `snapshot of strategy parameters at entry`:
    - TP threshold
    - SL threshold
    - IV/GEX thresholds
    - Other relevant params
- [ ] **Audit Trail:** Later, when thresholds change, can still see what old trades used

**Log Pattern:**
```
[MultiLeg] run_id=run_20241201_143022, package_id=SPY_STRADDLE_short_673_673_20241126, strategy=theta_harvester, params={"tp": 50.0, "sl": 200.0, "iv_collapse": 0.3}
```

---

## 🖥️ **UI/API Validation**

### **U1. Multi-Leg Open Positions Table**
**Check:**
- [ ] Table displays all open positions
- [ ] Columns correct:
  - Strategy
  - Symbol
  - Call Strike
  - Put Strike
  - Credit/Debit
  - P&L (with color coding)
  - Status (✅ Filled / ⏳ Pending)
- [ ] Real-time updates (every 3 seconds)
- [ ] P&L updates correctly
- [ ] Fill status updates correctly

### **U2. Multi-Leg Trade History Table**
**Check:**
- [ ] Table displays completed trades
- [ ] Columns correct:
  - Strategy
  - Entry Time
  - Exit Time
  - Total P&L (with %)
  - Duration
- [ ] Trades appear after exit
- [ ] P&L matches expected values
- [ ] Duration calculated correctly

### **U3. API Endpoints**
**Check:**
- [ ] `GET /options/positions` returns `multi_leg_positions` array
- [ ] `GET /trades/options/multi-leg` returns completed trades
- [ ] Both endpoints return 200 status
- [ ] Data structure matches UI expectations

**Verification:**
```bash
./test_multi_leg_api.sh
```

### **U4. Sorting/Pagination/Filters (NEW)**
**Check:**
- [ ] **Sorting Consistency:** P&L and time sorted consistently in UI vs API
- [ ] **Pagination:** If pagination exists, works correctly
- [ ] **Filters:** Filter by symbol/strategy/date matches number of records from API
- [ ] **No Hidden Trades:** UI doesn't hide any trades (all visible or paginated correctly)

**Verification:**
```bash
# Get all trades from API
curl http://localhost:8000/trades/options/multi-leg | jq '.trades | length'

# Check UI shows same count
# Filter by symbol
curl "http://localhost:8000/trades/options/multi-leg?symbol=SPY" | jq '.trades | length'

# Check UI filter shows same count
```

---

## 🚨 **Failure Mode Handling**

### **F1. Partial Fill Handling**
- [ ] System handles partial fills gracefully
- [ ] Position marked as "pending" until full fill
- [ ] Auto-exit waits for full fill
- [ ] Logs show fill status

### **F2. Order Rejection Handling**
- [ ] Rejected orders logged with reason
- [ ] Position marked as "broken"
- [ ] Auto-exit disabled for broken positions
- [ ] Alert generated for manual review

### **F3. Network Error Handling**
- [ ] Network errors caught and logged
- [ ] Retry logic with backoff
- [ ] System continues running after errors
- [ ] Positions remain tracked during errors

### **F4. Broker Throttling**
- [ ] Rate limiting detected
- [ ] Requests throttled appropriately
- [ ] No order loss due to throttling
- [ ] Logs show throttling events

---

## 📊 **Monitoring Commands**

### **Watch Logs**
```bash
# Multi-leg activity
tail -f logs/*.log | grep -i "multileg\|straddle\|strangle"

# Errors
tail -f logs/*.log | grep -i "error\|fail\|exception"

# Exit triggers
tail -f logs/*.log | grep -i "multilegexit\|closing.*straddle\|closing.*strangle"
```

### **Check API**
```bash
# Get positions
curl http://localhost:8000/options/positions | python3 -m json.tool

# Get trades
curl http://localhost:8000/trades/options/multi-leg | python3 -m json.tool

# Check status
curl http://localhost:8000/live/status | python3 -m json.tool
```

### **Check Dashboard**
- Open browser DevTools (F12)
- Check Console for JavaScript errors
- Check Network tab for API call failures
- Verify API responses match UI display

---

## ✅ **Success Indicators**

### **System Working Correctly**

1. **Logs show:**
   - Multi-leg execution messages
   - Fill confirmations
   - Auto-exit triggers with reasons
   - Combined P&L calculations
   - No unhandled exceptions

2. **Dashboard shows:**
   - Positions in "Multi-Leg Open Positions"
   - Real-time P&L updates
   - Completed trades in history
   - Fill status indicators
   - No UI errors

3. **API returns:**
   - Multi-leg positions array
   - Completed trades array
   - Correct data structures
   - No errors

4. **Database contains:**
   - All multi-leg positions
   - All completed trades
   - Correct P&L values
   - Matching timestamps

---

## 🎯 **Phase 1 Completion**

**Once ALL criteria pass:**

- ✅ No P&L mismatches
- ✅ All auto-exit triggers fire correctly
- ✅ No orphaned legs or stuck packages
- ✅ Zero unhandled exceptions
- ✅ Deterministic logging verified

**→ Proceed to Phase 2: Alpaca Paper-Live Validation**

---

## 📝 **Issue Tracking**

**Document any issues found:**

1. **Issue:** [Description]
   - **Severity:** Critical / High / Medium / Low
   - **Steps to Reproduce:** [Steps]
   - **Expected:** [Expected behavior]
   - **Actual:** [Actual behavior]
   - **Logs:** [Relevant log entries]
   - **Fix:** [Fix applied or pending]

---

**Ready to begin Phase 1 validation!** 🚀
