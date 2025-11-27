# Options Trading Setup Guide

## Overview

Options trading support has been added to the FutBot system. This allows you to trade options (calls and puts) through Alpaca.

## What Was Added

### 1. Options Data Feed (`core/live/options_data_feed.py`)
- Fetches options chain data
- Gets option quotes and Greeks (delta, gamma, theta, vega)
- Analyzes implied volatility

### 2. Options Broker Client (`core/live/options_broker_client.py`)
- Submits options orders (buy/sell contracts)
- Gets options positions
- Closes options positions

### 3. Options Agent (`core/agents/options_agent.py`)
- Analyzes options opportunities
- Filters by strike, expiration, delta, IV
- Calculates profit potential
- Generates PUT/CALL trade intents

## Prerequisites

1. ✅ **Alpaca Account with Options Trading Approved**
   - You mentioned you have this already!

2. **Alpaca API Keys**
   - Add to `.env`:
   ```bash
   ALPACA_API_KEY=your_api_key
   ALPACA_SECRET_KEY=your_secret_key
   ALPACA_BASE_URL=https://paper-api.alpaca.markets  # Paper trading
   # For live: https://api.alpaca.markets
   ```

3. **Python Dependencies**
   - `alpaca-py` (should already be installed)
   - `requests` (for options API calls)

## How Options Trading Works

### Your SPY $673 PUTS Example

The system will:
1. **Monitor SPY stock** for bearish signals
2. **When conditions align**:
   - Regime = DOWNTREND or EXPANSION
   - Bias = SHORT
   - Confidence ≥ 70%
   - Volatility = MEDIUM to HIGH
3. **Analyze options chain** for SPY PUTS
4. **Filter options** by:
   - Strike near current price (or OTM for your $673 PUT)
   - Expiration date (your 11/26/2025)
   - Delta (reasonable PUT delta, e.g., -0.30)
   - IV (not too high, not too low)
   - Days to expiration (7-45 days)
5. **Calculate profit potential** (your 70% target)
6. **Generate trade intent** if profit potential ≥ 50%
7. **Execute order** for the option contract

## Usage

### Start Options Trading

```bash
curl -X POST http://localhost:8000/options/start \
  -H "Content-Type: application/json" \
  -d '{
    "underlying_symbol": "SPY",
    "option_type": "put",
    "strike": 673.0,
    "expiration": "2025-11-26",
    "max_contracts": 1,
    "max_premium": 0.50
  }'
```

### Monitor Options Positions

```bash
curl http://localhost:8000/options/positions
```

### Close Options Position

```bash
curl -X POST http://localhost:8000/options/close \
  -H "Content-Type: application/json" \
  -d '{
    "option_symbol": "SPY251126P00673000",
    "quantity": 1
  }'
```

## Options Agent Configuration

The `OptionsAgent` can be configured with:

```python
{
    "min_confidence": 0.70,  # Minimum regime confidence
    "min_iv_percentile": 30.0,  # Minimum IV rank
    "max_iv_percentile": 90.0,  # Maximum IV rank
    "min_dte": 7,  # Minimum days to expiration
    "max_dte": 45,  # Maximum days to expiration
    "target_delta": -0.30,  # Target delta for PUTs (negative)
}
```

## Risk Management for Options

Options require different risk management than stocks:

1. **Position Sizing**: Based on premium paid, not stock price
2. **Stop Loss**: Based on premium loss % (e.g., 50% premium loss)
3. **Take Profit**: Based on premium gain % (e.g., 70% premium gain)
4. **Time Decay**: Exit before expiration if not profitable
5. **IV Crush**: Exit after earnings/events if IV drops

## Next Steps

1. **Test with Paper Trading**
   - Use Alpaca paper account first
   - Verify options chain data loads correctly
   - Test order execution

2. **Monitor First Trades**
   - Watch how the system identifies opportunities
   - Verify options are selected correctly
   - Check profit/loss tracking

3. **Adjust Parameters**
   - Tune delta range for your strategy
   - Adjust DTE range
   - Modify IV filters

## Important Notes

⚠️ **Options are complex and risky**:
- Can lose entire premium quickly
- Time decay works against you
- IV changes affect pricing
- Need to manage Greeks

⚠️ **Alpaca Options API**:
- May have different endpoints than documented
- Check Alpaca docs for latest API
- Some features may require live account

⚠️ **Testing Required**:
- Options API endpoints need to be verified
- Order execution needs testing
- Position tracking needs validation

## Support

If you encounter issues:
1. Check Alpaca API documentation for options
2. Verify your account has options trading enabled
3. Test with paper trading first
4. Monitor logs for errors

The system is ready for options trading once Alpaca API endpoints are confirmed!

