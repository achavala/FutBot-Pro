# Options Trading Pipeline - Diagnostic Checklist

**Goal:** Get at least one options trade to execute end-to-end in testing mode, and know why if it doesn't.

---

## Prerequisites

Before running diagnostics, ensure:

- ✅ **FastAPI server is running**
  ```bash
  python main.py --mode api --port 8000
  ```

- ✅ **Broker account configured**
  - Paper trading account enabled
  - Options trading permissions enabled
  - API keys set in environment:
    ```bash
    export ALPACA_API_KEY="your_key"
    export ALPACA_SECRET_KEY="your_secret"
    export ALPACA_BASE_URL="https://paper-api.alpaca.markets"
    ```

- ✅ **Market hours** (for live data)
  - Options trade during market hours (9:30 AM - 4:00 PM ET)
  - Or use cached data for offline testing

---

## Step 0: Run Automated Diagnostic First

**Always start here:**

```bash
python3 scripts/diagnose_options_pipeline.py
```

**Or use the wrapper:**

```bash
./scripts/diagnose_options_pipeline.sh
```

### Expected Output

**If PASS:**
```
✅ [EXECUTION] PASS (CASE_A): Broker accepted order: order_123
✅ [DATA] PASS (OK): Chain=150 contracts, Quote OK for SPY250117P00673000
✅ [DECISION] PASS (OK): Options trading active, 1 positions
```

**If FAIL:**
```
❌ [EXECUTION] FAIL (CASE_B): HTTP 400: invalid_symbol
```

**Action:**
- ✅ **If PASS** → You're done! Options trading is working.
- ❌ **If FAIL** → Go to the specific layer indicated below.

---

## Layer 1: Execution Plane

**Test:** API → BrokerClient → Broker → Response

**Case Mapping:**
- **CASE A** ✅ = Order accepted by broker
- **CASE B** ❌ = Broker error (invalid_symbol, insufficient_buying_power, etc.)
- **CASE C** ❌ = Request failed (no broker call in logs)

### Manual Test

```bash
curl -X POST http://localhost:8000/options/force_buy \
  -H "Content-Type: application/json" \
  -d '{"option_symbol": "SPY250117P00673000", "qty": 1}'
```

### Expected Response (Success)

```json
{
  "status": "submitted",
  "order_id": "abc123",
  "option_symbol": "SPY250117P00673000",
  "quantity": 1,
  "order_type": "limit",
  "message": "Order submitted successfully"
}
```

### Check Broker Account

- Log into Alpaca paper trading account
- Check "Orders" tab
- Should see order for `SPY250117P00673000`

### Log Patterns (Success)

```
INFO - Force buy request: option_symbol=SPY250117P00673000, qty=1
INFO - Submitting order to broker...
INFO - Broker response: order_id=abc123, status=submitted
```

### Common Failures

**CASE B: Broker Error**

| Error | Cause | Solution |
|-------|-------|----------|
| `invalid_symbol` | Wrong option symbol format | Use OCC format: `SPY250117P00673000` |
| `insufficient_buying_power` | Not enough cash | Check account balance |
| `account_not_permissioned` | Options not enabled | Enable options trading in account |
| `market_closed` | Outside trading hours | Try during 9:30 AM - 4:00 PM ET |

**CASE C: No Broker Call**

- Check logs for `ForceBuyRequest` or `force_buy`
- If missing → Handler not registered
- If present but no broker call → Check handler logic

### Fix Execution Plane First

**Do not proceed to Layer 2 until Layer 1 passes.**

---

## Layer 2: Data Plane

**Test:** Options Chain / Quotes / Greeks

**Case Mapping:**
- **CASE D** ❌ = Chain fetch = 0 or errors
- **CASE E** ❌ = Quotes/Greeks fetch = 0 or errors

### Manual Test: Chain

```bash
curl "http://localhost:8000/options/chain?symbol=SPY&option_type=put"
```

### Expected Response (Success)

```json
[
  {
    "symbol": "SPY250117P00673000",
    "strike_price": 673.0,
    "expiration_date": "2025-01-17",
    "option_type": "put"
  },
  {
    "symbol": "SPY250117P00674000",
    "strike_price": 674.0,
    "expiration_date": "2025-01-17",
    "option_type": "put"
  },
  ...
]
```

**Check:** Contract count > 0

### Manual Test: Quote

```bash
curl "http://localhost:8000/options/quote?option_symbol=SPY250117P00673000"
```

### Expected Response (Success)

```json
{
  "bid": 0.35,
  "ask": 0.40,
  "mid": 0.38,
  "open_interest": 1250,
  "volume": 45
}
```

**Check:** Has `bid`, `ask`, or `mid`

### Log Patterns (Success)

```
INFO - OptionsAgent: Fetching options chain for SPY PUTs...
INFO - OptionsAgent: Received 150 contracts from options chain
INFO - OptionsAgent: Fetching quotes and Greeks for 150 contracts...
INFO - OptionsAgent: Fetched 145 quotes, 140 Greeks
```

### Common Failures

**CASE D: Chain Fetch = 0**

- Check Alpaca API credentials
- Check API endpoint format
- Check market hours
- Review logs: `tail -f logs/*.log | grep -i 'options.*chain'`

**CASE E: Quotes/Greeks = 0**

- Check symbol format (OCC format)
- Check rate limits
- Review logs: `tail -f logs/*.log | grep -i 'quote|greeks'`

### Fix Data Plane Before Proceeding

**Do not proceed to Layer 3 until Layer 2 passes.**

---

## Layer 3: Decision Plane

**Test:** Agents, Filters, Selector, Scheduler

**Case Mapping:**
- **CASE F** ❌ = CandidatesEvaluated = 0 (agent not called or pre-filtered)
- **CASE G** ❌ = CandidatesEvaluated > 0, but CandidatesPassed = 0 (filters too strict)
- **CASE H** ❌ = ACCEPT but no order (risk manager or execution boundary)
- **CASE I** ❌ = Order attempted but broker rejects

### Start Options Trading

```bash
curl -X POST http://localhost:8000/options/start \
  -H "Content-Type: application/json" \
  -d '{
    "underlying_symbol": "SPY",
    "option_type": "put",
    "testing_mode": true
  }'
```

### Monitor Logs

```bash
tail -f logs/*.log | grep -i "optionsagent"
```

### Expected Log Sequence (Success)

```
INFO - OptionsAgent.evaluate() called for SPY: regime=trend, confidence=78.50%, trend=down, bias=short, volatility=medium
INFO - OptionsAgent: Agent alignment check: {'trend_agent': True, 'mean_reversion_agent': False, 'volatility_agent': True}, aligned=True
INFO - OptionsAgent: Fetching options chain for SPY PUTs...
INFO - OptionsAgent: Received 150 contracts from options chain
INFO - OptionsAgent: Fetching quotes and Greeks for 150 contracts...
INFO - OptionsAgent: Fetched 145 quotes, 140 Greeks
INFO - OptionsAgent: Evaluating contract SPY251126P00673000: strike=673.0, expiry=2025-11-26, DTE=45, bid=0.35, ask=0.40, mid=0.38, spread=13.16%, OI=1250, volume=45, delta=-0.32, theta=-0.0012 (0.32%/day), gamma=0.0023, IV=45.23%
INFO - OptionsAgent: Evaluated 150 candidates, 5 passed filters
ACCEPT SPY251126P00673000: Validation passed - spread=8.50%, OI=1250, volume=45, delta=-0.32, DTE=45, IV=45.23%, premium=$0.38
INFO - ACCEPT SPY251126P00673000: Validation passed, generating trade intent
INFO - SubmittingOrder: symbol=SPY251126P00673000, qty=1, side=BUY
INFO - Broker response: order_id=abc123, status=submitted
```

### Case F: CandidatesEvaluated = 0

**Symptoms:**
- No "Evaluating contract" logs
- No "CandidatesEvaluated" logs
- Agent may not be called

**Check:**
```bash
# Verify agent is registered
curl http://localhost:8000/agents | grep -i options

# Check if agent is being called
tail -f logs/*.log | grep -i "optionsagent.evaluate"
```

**Solutions:**
- Check scheduler agent list
- Check agent registration in `ui/fastapi_app.py`
- Check agent wiring in `core/live/scheduler.py`

### Case G: CandidatesEvaluated > 0, CandidatesPassed = 0

**Symptoms:**
```
INFO - OptionsAgent: Evaluated 150 candidates, 0 passed filters
REJECT SPY251126P00673000: Spread too wide: 13.16% > 10.00%
REJECT SPY251126P00673000: Open interest too low: 45 < 100
```

**Check Runtime Config:**

In testing mode, you should see these values:
```
RuntimeConfig:
  min_open_interest = 1 (was 100)
  min_volume = 0 (was 10)
  max_spread_pct = 40% (was 10%)
  min_dte = 1 (was 7)
  max_dte = 90 (was 45)
  theta_threshold = 1.0 (was 0.05)
  required_alignment = 1-of-3 (was 2-of-3)
```

**Solutions:**
- Verify `testing_mode=True` is passed to `OptionRiskProfile`
- Check `core/config/asset_profiles.py` - `__post_init__()` method
- Check REJECT reasons - may need to relax further

### Case H: ACCEPT but No Order

**Symptoms:**
```
ACCEPT SPY251126P00673000: Validation passed
INFO - ACCEPT SPY251126P00673000: Validation passed, generating trade intent
# But no "SubmittingOrder" log
```

**Check:**
- Risk manager vetoing trades
- Dry-run mode enabled
- Execution boundary logic
- Add logging around final decision

**Solutions:**
- Check `core/live/scheduler.py` - execution boundary
- Check risk manager logs
- Check for dry-run flags

### Case I: Order Attempted but Broker Rejects

**Symptoms:**
```
INFO - SubmittingOrder: symbol=SPY251126P00673000, qty=1, side=BUY
ERROR - BrokerError: invalid_symbol
```

**Check:**
- Compare force_buy vs OptionsAgent order format
- Symbol format differences
- Quantity differences
- Order type differences

**Solutions:**
- Adjust production path to mirror force_buy
- Check symbol format conversion
- Verify order type (LIMIT vs MARKET)

---

## Success Criteria

**At least one auto options trade executed in testing mode for SPY within 5 minutes.**

**Logs must show:**

1. ✅ Chain & quotes fetched
   ```
   OptionsAgent: Received 150 contracts from options chain
   OptionsAgent: Fetched 145 quotes, 140 Greeks
   ```

2. ✅ Candidates evaluated and passed
   ```
   OptionsAgent: Evaluated 150 candidates, 5 passed filters
   ```

3. ✅ Selector decision
   ```
   ACCEPT SPY251126P00673000: Validation passed
   ```

4. ✅ Order submitted
   ```
   SubmittingOrder: symbol=SPY251126P00673000, qty=1, side=BUY
   ```

5. ✅ Broker acknowledgment
   ```
   Broker response: order_id=abc123, status=submitted
   ```

**Broker account must show:**
- Order appears in "Orders" tab
- Order status is "filled" or "pending"

---

## Quick Reference

### Exit Codes

- `0` = All layers pass
- `1` = Execution plane failure
- `2` = Data plane failure
- `3` = Decision plane failure

### Key Commands

```bash
# Run diagnostic
python3 scripts/diagnose_options_pipeline.py

# Monitor logs
tail -f logs/*.log | grep -i "optionsagent"

# Check agents
curl http://localhost:8000/agents

# Force buy test
curl -X POST http://localhost:8000/options/force_buy \
  -H "Content-Type: application/json" \
  -d '{"option_symbol": "SPY250117P00673000", "qty": 1}'

# Start options trading
curl -X POST http://localhost:8000/options/start \
  -H "Content-Type: application/json" \
  -d '{"underlying_symbol": "SPY", "option_type": "put", "testing_mode": true}'
```

---

## Troubleshooting

### No logs at all
- Check logging configuration
- Ensure logs directory exists
- Check log file permissions

### Agent not in agents list
- Check `ui/fastapi_app.py` - ensure OptionsAgent is added
- Restart FastAPI server

### Testing mode not applying
- Check `OptionRiskProfile.__post_init__()` 
- Verify `testing_mode=True` is passed
- Check config loading order

### All contracts rejected
- Check REJECT reasons in logs
- Verify runtime config matches testing mode
- Check pre-filters (DTE range, option type, etc.)

### ACCEPT but no order
- Check risk manager logs
- Check execution boundary
- Add logging around final decision
