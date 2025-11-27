# Force Trades Guide - Making Options Actually Execute

## Problem: System Too Strict, No Trades

After implementing comprehensive risk management, the system may be rejecting all trades. This guide helps you force trades to test the pipeline.

## Quick Checklist

### 1. Confirm Agent is Being Called

```bash
# Check if options trading is active
curl http://localhost:8000/live/status

# Check agents
curl http://localhost:8000/agents

# Watch logs for OptionsAgent calls
tail -f logs/*.log | grep -i "optionsagent"
```

**Look for:**
- `OptionsAgent.evaluate() called for SPY`
- `OptionsAgent: Fetching options chain`
- `OptionsAgent: Evaluating contract`

**If you don't see these:**
- Agent may not be wired into the trading loop
- Check that OptionsAgent is added to `live_loop.agents`

### 2. Check Options Chain Availability

```bash
curl "http://localhost:8000/options/chain?symbol=SPY&option_type=put"
```

**Should see:**
- Array of contracts with strikes, expirations
- If empty → API issue or market closed

### 3. Enable Ultra-Loose Testing Mode

Testing mode now uses VERY relaxed filters:

```bash
curl -X POST http://localhost:8000/options/start \
  -H "Content-Type: application/json" \
  -d '{
    "underlying_symbol": "SPY",
    "option_type": "put",
    "testing_mode": true
  }'
```

**Testing mode relaxes:**
- `min_open_interest`: 100 → 1
- `min_volume`: 10 → 0
- `max_spread_pct`: 10% → 40%
- IV filter: Disabled (0-100%)
- DTE range: 1-90 days
- Theta filter: Very high (basically disabled)
- Agent alignment: 1-of-3 (was 2-of-3)

### 4. Force Buy (Bypass All Filters)

Test broker connectivity directly:

```bash
curl -X POST http://localhost:8000/options/force_buy \
  -H "Content-Type: application/json" \
  -d '{
    "option_symbol": "SPY250117P00673000",
    "qty": 1,
    "limit_price": 0.40
  }'
```

**This:**
- Bypasses all filters
- Tests broker connectivity
- Tests order execution
- Tests symbol formatting

**If this fails:**
- Check Alpaca API credentials
- Check options trading permissions
- Check symbol format
- Check market hours

**If this works:**
- Broker is fine
- Issue is in signal/validation pipeline

### 5. Run Backtest

```bash
python3 backtesting/run_options_demo.py \
  --underlying SPY \
  --start 2025-01-02 \
  --end 2025-01-10 \
  --testing-mode
```

**This shows:**
- If pipeline works on historical data
- What trades would be generated
- If filters are the issue

### 6. Watch Detailed Logs

With trace logging enabled, you'll see:

```
INFO - OptionsAgent.evaluate() called for SPY: regime=trend, confidence=78.50%, trend=down, bias=short, volatility=medium
INFO - OptionsAgent: Agent alignment check: {'trend_agent': True, 'mean_reversion_agent': False, 'volatility_agent': True}, aligned=True
INFO - OptionsAgent: Fetching options chain for SPY PUTs...
INFO - OptionsAgent: Received 150 contracts from options chain
INFO - OptionsAgent: Fetching quotes and Greeks for 150 contracts...
INFO - OptionsAgent: Fetched 145 quotes, 140 Greeks
INFO - OptionsAgent: Evaluating contract SPY251126P00673000: strike=673.0, expiry=2025-11-26, DTE=45, bid=0.35, ask=0.40, mid=0.38, spread=13.16%, OI=1250, volume=45, delta=-0.32, theta=-0.0012 (0.32%/day), gamma=0.0023, IV=45.23%
REJECT SPY251126P00673000: Spread too wide: 13.16% > 10.00%
```

**What to look for:**
- How many contracts are evaluated?
- What's the most common rejection reason?
- Do any contracts reach ACCEPT?

## Debugging Steps

### Step 1: Verify Agent is Called

```bash
# Start options trading
curl -X POST http://localhost:8000/options/start \
  -H "Content-Type: application/json" \
  -d '{"underlying_symbol": "SPY", "option_type": "put", "testing_mode": true}'

# Watch logs
tail -f logs/*.log | grep -i "optionsagent"
```

**Expected:**
- Should see `OptionsAgent.evaluate() called` every bar
- If not → agent not wired into loop

### Step 2: Check Options Chain

```bash
curl "http://localhost:8000/options/chain?symbol=SPY&option_type=put" | python3 -m json.tool | head -50
```

**Expected:**
- Should see contracts with strikes, expirations
- If empty → API issue

### Step 3: Force Buy Test

```bash
# Get a real option symbol from chain
OPTION_SYMBOL="SPY250117P00673000"  # Replace with actual symbol

curl -X POST http://localhost:8000/options/force_buy \
  -H "Content-Type: application/json" \
  -d "{
    \"option_symbol\": \"$OPTION_SYMBOL\",
    \"qty\": 1
  }"
```

**Expected:**
- Order should submit
- If fails → broker/API issue
- If succeeds → pipeline issue

### Step 4: Analyze Logs

Look for patterns:

**Pattern 1: No contracts evaluated**
```
OptionsAgent: Received 0 contracts from options chain
```
→ Options chain fetch failing

**Pattern 2: All contracts rejected**
```
OptionsAgent: Evaluated 150 candidates, 0 passed filters
REJECT: Spread too wide
REJECT: Open interest too low
```
→ Filters too strict (use testing mode)

**Pattern 3: Agent not called**
```
(No OptionsAgent logs at all)
```
→ Agent not wired into loop

**Pattern 4: Agent alignment failing**
```
OptionsAgent: Agent alignment failed - trend=False, mr=False, vol=True
```
→ Need 2-of-3 agents (1-of-3 in testing mode)

## Quick Fixes

### Fix 1: Agent Not Called

Ensure OptionsAgent is added to the loop:

```python
# In ui/fastapi_app.py, after starting live trading:
if bot_manager.live_loop:
    bot_manager.live_loop.agents.append(options_agent)
```

### Fix 2: All Contracts Rejected

Enable testing mode with ultra-loose filters (already implemented).

### Fix 3: Options Chain Empty

- Check Alpaca API credentials
- Check market hours
- Check symbol format (SPY, not SPXW)
- Verify options trading enabled in Alpaca account

### Fix 4: Force Buy Fails

- Check Alpaca options API endpoint format
- Verify option symbol format
- Check buying power
- Check account permissions

## Expected Success Log

```
INFO - OptionsAgent.evaluate() called for SPY: regime=trend, confidence=78.50%, trend=down, bias=short, volatility=medium
INFO - OptionsAgent: Agent alignment check: {'trend_agent': True, 'mean_reversion_agent': False, 'volatility_agent': True}, aligned=True
INFO - OptionsAgent: Fetching options chain for SPY PUTs...
INFO - OptionsAgent: Received 150 contracts from options chain
INFO - OptionsAgent: Fetching quotes and Greeks for 150 contracts...
INFO - OptionsAgent: Fetched 145 quotes, 140 Greeks
INFO - OptionsAgent: Contract selector picked: SPY251126P00673000
ACCEPT SPY251126P00673000: Validation passed - spread=8.50%, OI=1250, volume=45, delta=-0.32, DTE=45, IV=45.23%, premium=$0.38
INFO - ACCEPT SPY251126P00673000: Validation passed, generating trade intent
```

## Next Steps

1. **Start with force buy** - Test broker connectivity
2. **Enable testing mode** - Loosen all filters
3. **Watch logs** - See exactly what's happening
4. **Run backtest** - Test on historical data
5. **Tighten filters** - Once you see trades, gradually tighten

The system is now instrumented to show you exactly what's happening at every step!

