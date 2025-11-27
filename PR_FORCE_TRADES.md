# PR: Add "Force Trades" debug package for OptionsAgent & end-to-end validation

## Summary

This change introduces a full "Force Trades" toolkit to debug and verify the entire options trading pipeline end-to-end:

- **Ultra-loose testing mode** so trades are easy to trigger
- **Deep trace logging** at each stage of the pipeline
- **A force buy endpoint** that bypasses filters to test broker connectivity
- **Fixed agent wiring** so OptionsAgent receives base agent signals
- **A backtest script** to show hypothetical trades
- **A troubleshooting guide + diagnostic script** for repeatable debugging

## Details

### 1. Ultra-loose testing mode

Testing mode is designed to maximize the chance of seeing trades by relaxing almost all filters:

- `min_open_interest`: 100 → 1
- `min_volume`: 10 → 0
- `max_spread_pct`: 10% → 40%
- Theta filter: effectively disabled (theta_threshold = 1.0)
- DTE range widened to 1–90 days
- Agent alignment relaxed from 2-of-3 → 1-of-3

This is strictly for testing/diagnostics, not production risk settings.

**Files changed:**
- `core/config/asset_profiles.py` - Added `testing_mode` flag and relaxed defaults

### 2. Enhanced trace logging

Added detailed logging so we can see exactly what the OptionsAgent is doing on every cycle:

- Options chain fetch count
- Quotes/Greeks fetch count
- Number of candidate contracts evaluated
- Number of contracts passing filters
- Which contract(s) the selector chooses
- ACCEPT / REJECT decisions with human-readable reasons

This gives a full trace from:

"Scheduler tick" → "Agent called" → "Data fetched" → "Contracts evaluated" → "Decision made".

**Files changed:**
- `core/agents/options_agent.py` - Added comprehensive logging throughout evaluation pipeline

### 3. Force buy endpoint

New endpoint to test the execution plane in isolation:

**Endpoint:** `POST /options/force_buy`

**Behavior:**
- Bypasses all filters, agents, and alignment logic
- Sends a direct order to the broker for a given option symbol and quantity
- Validates:
  - Broker connectivity
  - Auth/permissions
  - Order creation/translation
  - Response handling / error paths

**Example usage:**
```bash
curl -X POST http://localhost:8000/options/force_buy \
  -H "Content-Type: application/json" \
  -d '{"option_symbol": "SPY250117P00673000", "qty": 1}'
```

**Files changed:**
- `ui/fastapi_app.py` - Added `/options/force_buy` endpoint

### 4. Agent wiring & scheduler integration

Fixed the pipeline so that OptionsAgent actually receives base agent signals:

- OptionsAgent is now plugged into the main scheduler loop
- Base agent signals are computed and updated before OptionsAgent evaluation
- OptionsAgent can honor alignment rules (now 1-of-3 in testing mode)

With logging enabled, you can see:
- Scheduler tick
- Base agent signals
- Alignment evaluation
- OptionsAgent evaluation outcome

**Files changed:**
- `core/live/scheduler.py` - Added logic to update options agents with base agent signals before evaluation
- `ui/fastapi_app.py` - Improved options agent integration into trading loop

### 5. Backtest script

Improved backtesting support:

- Fixed flag handling (no more ignored/incorrect flags)
- Backtest now clearly shows which trades would have been generated
- Uses the same rules as the live engine (minus broker execution) for consistency

This is useful to verify:
- Filters & selector behavior
- Agent alignment logic
- That relaxing filters in testing mode actually produces candidates

**Files changed:**
- `backtesting/run_options_demo.py` - Fixed flag handling and improved output

### 6. Documentation & diagnostics

New docs + helper script:

**OPTIONS_FORCE_TRADES_GUIDE.md**
- End-to-end troubleshooting guide
- How to use testing mode, logs, backtests, and force buy together
- Typical failure patterns and where to look (data, filters, alignment, broker)

**scripts/check_options_agent_called.sh**
- Simple diagnostic script to verify that the OptionsAgent is being invoked by the scheduler
- Helps quickly distinguish "agent not wired" vs "no candidates passed filters"

**Files added:**
- `OPTIONS_FORCE_TRADES_GUIDE.md`
- `scripts/check_options_agent_called.sh`

## Quick Start / How to Verify E2E

### 1. Test broker connectivity (force buy)

```bash
curl -X POST http://localhost:8000/options/force_buy \
  -H "Content-Type: application/json" \
  -d '{"option_symbol": "SPY250117P00673000", "qty": 1}'
```

- Confirms broker auth + order execution path works.

### 2. Run OptionsAgent in testing mode

```bash
curl -X POST http://localhost:8000/options/start \
  -H "Content-Type: application/json" \
  -d '{"underlying_symbol": "SPY", "option_type": "put", "testing_mode": true}'
```

### 3. Watch the logs

```bash
tail -f logs/*.log | grep -i "optionsagent"
```

You should see:
- Whether the agent is called each cycle
- Options chain + quotes/Greeks fetch counts
- Every contract evaluated
- REJECT reasons for failed contracts
- Which contracts pass validation
- Agent alignment status
- A full trace from signal → filters → selector → (optionally) execution

## Testing

### Manual Testing Checklist

- [ ] Force buy endpoint successfully submits order to broker
- [ ] OptionsAgent is called on each scheduler tick (check logs)
- [ ] Testing mode relaxes filters appropriately
- [ ] Trace logging shows full pipeline execution
- [ ] Backtest script generates expected trades
- [ ] Agent alignment works correctly (1-of-3 in testing mode)

### Expected Log Output (Success)

```
INFO - OptionsAgent.evaluate() called for SPY: regime=trend, confidence=78.50%, trend=down, bias=short, volatility=medium
INFO - OptionsAgent: Agent alignment check: {'trend_agent': True, 'mean_reversion_agent': False, 'volatility_agent': True}, aligned=True
INFO - OptionsAgent: Fetching options chain for SPY PUTs...
INFO - OptionsAgent: Received 150 contracts from options chain
INFO - OptionsAgent: Fetching quotes and Greeks for 150 contracts...
INFO - OptionsAgent: Fetched 145 quotes, 140 Greeks
INFO - OptionsAgent: Evaluating contract SPY251126P00673000: strike=673.0, expiry=2025-11-26, DTE=45, bid=0.35, ask=0.40, mid=0.38, spread=13.16%, OI=1250, volume=45, delta=-0.32, theta=-0.0012 (0.32%/day), gamma=0.0023, IV=45.23%
ACCEPT SPY251126P00673000: Validation passed - spread=8.50%, OI=1250, volume=45, delta=-0.32, DTE=45, IV=45.23%, premium=$0.38
INFO - ACCEPT SPY251126P00673000: Validation passed, generating trade intent
```

## Files Changed

### Core Changes
- `core/config/asset_profiles.py` - Added testing mode with ultra-loose filters
- `core/agents/options_agent.py` - Enhanced trace logging throughout
- `core/live/scheduler.py` - Fixed agent wiring to pass base agent signals

### API Changes
- `ui/fastapi_app.py` - Added `/options/force_buy` endpoint and improved agent integration

### Scripts & Documentation
- `backtesting/run_options_demo.py` - Fixed flag handling
- `scripts/check_options_agent_called.sh` - New diagnostic script
- `OPTIONS_FORCE_TRADES_GUIDE.md` - New troubleshooting guide

## Breaking Changes

None. This is purely additive - all new features are opt-in via testing mode or new endpoints.

## Related Issues

- Addresses issue where OptionsAgent was too strict and not generating trades
- Provides debugging tools to diagnose why trades aren't executing
- Enables end-to-end validation of options trading pipeline

## Notes

- Testing mode should **never** be used in production
- Force buy endpoint bypasses all safety checks - use with caution
- All logging is at INFO/DEBUG level - adjust log levels as needed

