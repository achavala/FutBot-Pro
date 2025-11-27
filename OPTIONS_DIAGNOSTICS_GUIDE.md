# Options Trading Diagnostics Guide

## Problem: No Trades Executing

After implementing comprehensive risk management, the system may be too strict and rejecting all trades. This guide helps you diagnose and fix the issue.

## Quick Diagnostics

### 1. Check Options Chain Availability

```bash
curl "http://localhost:8000/options/chain?symbol=SPY&option_type=put"
```

**What to look for:**
- Do you see contracts? (Should see 100+ for SPY)
- Do contracts have bid/ask prices?
- Do contracts have open interest and volume?

**If empty:**
- Alpaca API may not be returning options data
- Market may be closed
- Symbol format may be wrong

### 2. Check Current Regime

```bash
curl http://localhost:8000/regime
```

**What to look for:**
- `is_valid: true` (not false)
- `confidence: > 0.70` (for options trading)
- `regime_type: "trend"` or `"expansion"` (not "compression")
- `trend_direction: "down"` (for PUT trades)
- `bias: "short"` (for PUT trades)
- `volatility_level: "medium"` or `"high"` (not "low")

**If regime is stuck:**
- May need more bars (wait for 30+ bars)
- Market may be in choppy/neutral state

### 3. Enable Testing Mode

Testing mode relaxes all filters to help diagnose issues:

```bash
# Enable testing mode
curl -X POST http://localhost:8000/options/testing_mode \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'

# Start options trading with testing mode
curl -X POST http://localhost:8000/options/start \
  -H "Content-Type: application/json" \
  -d '{
    "underlying_symbol": "SPY",
    "option_type": "put",
    "testing_mode": true
  }'
```

**Testing mode relaxes:**
- `min_open_interest`: 100 → 10
- `min_volume`: 10 → 1
- `max_spread_pct`: 10% → 20%
- IV filter: Disabled (0-100%)
- DTE range: 3-60 days (was 7-45)
- Agent alignment: 1-of-3 (was 2-of-3)

### 4. Check Logs for Trace Output

With trace logging enabled, you'll see:

```
INFO - OptionsAgent.evaluate() called for SPY: regime=trend, confidence=75.00%, trend=down, bias=short, volatility=medium
INFO - OptionsAgent: Agent alignment check: {'trend_agent': True, 'mean_reversion_agent': False, 'volatility_agent': True}, aligned=True
INFO - OptionsAgent: Evaluating contract SPY251126P00673000: strike=673.0, expiry=2025-11-26, DTE=45, bid=0.35, ask=0.40, mid=0.38, spread=13.16%, OI=1250, volume=45, delta=-0.32, theta=-0.0012 (0.32%/day), gamma=0.0023, IV=45.23%
REJECT SPY251126P00673000: Spread too wide: 13.16% > 10.00%
```

**What to look for:**
- Are contracts being evaluated?
- What's the rejection reason?
- Are any contracts passing validation?

## Common Issues & Solutions

### Issue 1: No Options Chain Data

**Symptoms:**
- `GET /options/chain` returns empty array
- Logs show "No options chain available"

**Solutions:**
1. Verify Alpaca options API is working
2. Check market hours (options trade during market hours)
3. Verify symbol format (SPY, not SPXW)
4. Check Alpaca account has options trading enabled

### Issue 2: All Contracts Rejected - Spread Too Wide

**Symptoms:**
- Logs show: `REJECT: Spread too wide: 15.23% > 10.00%`
- Many contracts evaluated but all rejected

**Solutions:**
1. Enable testing mode (increases max_spread_pct to 20%)
2. Lower `max_spread_pct` in OptionRiskProfile
3. Focus on more liquid strikes (ATM, near ATM)

### Issue 3: All Contracts Rejected - Low Open Interest

**Symptoms:**
- Logs show: `REJECT: Open interest too low: 45 < 100`

**Solutions:**
1. Enable testing mode (lowers min_open_interest to 10)
2. Lower `min_open_interest` in OptionRiskProfile
3. Trade more liquid underlyings (SPY, QQQ)

### Issue 4: Agent Alignment Failing

**Symptoms:**
- Logs show: `OptionsAgent: Agent alignment failed`
- `alignment_count: 1/2 required`

**Solutions:**
1. Enable testing mode (requires 1-of-3 instead of 2-of-3)
2. Check if base agents (TrendAgent, MeanReversionAgent, VolatilityAgent) are active
3. Wait for better market conditions where agents align

### Issue 5: Regime Not Valid or Low Confidence

**Symptoms:**
- Logs show: `OptionsAgent: Regime not valid` or `Confidence too low: 45.00% < 70.00%`

**Solutions:**
1. Wait for more bars to be collected (need 30+)
2. Lower `min_confidence` in OptionsAgent config
3. Check if regime engine is computing features correctly

### Issue 6: No Bearish Conditions

**Symptoms:**
- Regime shows `trend_direction: "up"` or `bias: "long"`
- OptionsAgent returns early (not bearish)

**Solutions:**
1. Wait for bearish market conditions
2. System is working correctly - it's avoiding trades in bullish conditions
3. For testing, you could temporarily allow bullish PUTs (not recommended)

## Step-by-Step Debugging

### Step 1: Verify Data Flow

```bash
# 1. Check if bot is running
curl http://localhost:8000/health

# 2. Check regime
curl http://localhost:8000/regime

# 3. Check options chain
curl "http://localhost:8000/options/chain?symbol=SPY&option_type=put"
```

### Step 2: Enable Testing Mode & Trace Logging

```bash
# Enable testing mode
curl -X POST http://localhost:8000/options/testing_mode \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'

# Start options trading
curl -X POST http://localhost:8000/options/start \
  -H "Content-Type: application/json" \
  -d '{
    "underlying_symbol": "SPY",
    "option_type": "put",
    "testing_mode": true
  }'
```

### Step 3: Monitor Logs

Watch the logs for:
- `OptionsAgent.evaluate()` calls
- Contract evaluations with full details
- REJECT/ACCEPT messages

### Step 4: Run Backtest

```bash
python3 backtesting/run_options_demo.py \
  --underlying SPY \
  --start 2025-10-01 \
  --end 2025-10-31 \
  --testing-mode
```

This will show if the pipeline works on historical data.

## Expected Log Output (Success)

```
INFO - OptionsAgent.evaluate() called for SPY: regime=trend, confidence=78.50%, trend=down, bias=short, volatility=medium
INFO - OptionsAgent: Agent alignment check: {'trend_agent': True, 'mean_reversion_agent': False, 'volatility_agent': True}, aligned=True
INFO - OptionsAgent: Evaluating contract SPY251126P00673000: strike=673.0, expiry=2025-11-26, DTE=45, bid=0.35, ask=0.40, mid=0.38, spread=13.16%, OI=1250, volume=45, delta=-0.32, theta=-0.0012 (0.32%/day), gamma=0.0023, IV=45.23%
ACCEPT SPY251126P00673000: Validation passed - spread=13.16%, OI=1250, volume=45, delta=-0.32, DTE=45, IV=45.23%, premium=$0.38
INFO - ACCEPT SPY251126P00673000: Validation passed, generating trade intent
```

## Next Steps

1. **If you see contracts being evaluated but all rejected:**
   - Check the rejection reasons in logs
   - Adjust OptionRiskProfile thresholds
   - Enable testing mode

2. **If you see no contracts being evaluated:**
   - Check options chain availability
   - Check agent alignment
   - Check regime validity

3. **If you see trades in backtest but not live:**
   - Check market hours
   - Check Alpaca API connectivity
   - Check broker permissions

4. **If everything looks good but still no trades:**
   - Check risk manager (kill switch, daily limits)
   - Check broker order execution logs
   - Verify Alpaca options trading is enabled

The trace logging will tell you exactly where the pipeline is failing!

