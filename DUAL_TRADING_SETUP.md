# Dual Trading Setup: Paper + Live Trading Simultaneously

This guide explains how to set up and use both **paper trading** and **live trading** with Alpaca at the same time.

## Overview

You can now run both paper and live trading simultaneously using the same FutBot instance. This is useful for:
- Testing strategies on paper while running live trades
- Comparing paper vs live performance
- Having a backup trading system

## Method 1: Using API Requests (Recommended)

You can specify which mode (paper or live) when starting trading via API requests.

### Start Paper Trading

```bash
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["QQQ"],
    "broker_type": "alpaca",
    "api_key": "your_paper_api_key",
    "api_secret": "your_paper_secret",
    "base_url": "https://paper-api.alpaca.markets"
  }'
```

### Start Live Trading

```bash
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["QQQ"],
    "broker_type": "alpaca",
    "api_key": "your_live_api_key",
    "api_secret": "your_live_secret",
    "base_url": "https://api.alpaca.markets"
  }'
```

**Note:** You can use the same API keys if your Alpaca account supports both paper and live, or use different keys for separate accounts.

## Method 2: Using Environment Variables + Override

Set your default mode in environment variables, then override per request:

### Set Default to Paper Trading

In your `.env` file:
```bash
ALPACA_API_KEY=your_api_key
ALPACA_SECRET_KEY=your_secret_key
ALPACA_BASE_URL=https://paper-api.alpaca.markets  # Default to paper
```

### Start Paper Trading (uses default from .env)

```bash
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["QQQ"],
    "broker_type": "alpaca"
  }'
```

### Start Live Trading (overrides default)

```bash
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["QQQ"],
    "broker_type": "alpaca",
    "base_url": "https://api.alpaca.markets"
  }'
```

## Method 3: Two Separate Server Instances

Run two separate FutBot instances on different ports, each with different environment variables.

### Instance 1: Paper Trading (Port 8000)

Create `.env.paper`:
```bash
ALPACA_API_KEY=your_paper_api_key
ALPACA_SECRET_KEY=your_paper_secret_key
ALPACA_BASE_URL=https://paper-api.alpaca.markets
```

Start server:
```bash
# Load paper environment
export $(cat .env.paper | xargs)
python main.py --mode api --port 8000
```

### Instance 2: Live Trading (Port 8001)

Create `.env.live`:
```bash
ALPACA_API_KEY=your_live_api_key
ALPACA_SECRET_KEY=your_live_secret_key
ALPACA_BASE_URL=https://api.alpaca.markets
```

Start server:
```bash
# Load live environment
export $(cat .env.live | xargs)
python main.py --mode api --port 8001
```

### Access Both Dashboards

- Paper Trading: http://localhost:8000/visualizations/dashboard
- Live Trading: http://localhost:8001/visualizations/dashboard

## Using the Dashboard

The dashboard's "Start Live" button will use the environment variables by default. To switch between paper and live:

1. **Via API directly** (recommended for switching):
   - Use the API endpoints with `base_url` parameter
   - Or modify the dashboard JavaScript to include `base_url` in requests

2. **Via Environment Variables**:
   - Change `ALPACA_BASE_URL` in your `.env` file
   - Restart the server

## Challenge Mode

Challenge mode also supports `base_url`:

```bash
curl -X POST http://localhost:8000/challenge/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["QQQ"],
    "broker_type": "alpaca",
    "api_key": "your_api_key",
    "api_secret": "your_secret",
    "base_url": "https://api.alpaca.markets",
    "initial_capital": 1000.0,
    "target_capital": 100000.0
  }'
```

## Important Notes

1. **API Keys**: 
   - Paper and live trading typically use **different API keys**
   - Paper keys are free and unlimited
   - Live keys require a funded account

2. **Rate Limits**:
   - Both paper and live share the same rate limits if using the same account
   - Using separate accounts avoids this

3. **Portfolio Separation**:
   - Paper and live portfolios are completely separate
   - Each maintains its own position tracking and P&L

4. **Data Feeds**:
   - Both can use the same data feed (Alpaca provides data for both)
   - Or use separate data sources if needed

## Railway Deployment

For Railway, you can:

1. **Single Instance with API Override**:
   - Set default `ALPACA_BASE_URL` in Railway environment variables
   - Override per request using `base_url` parameter

2. **Two Separate Railway Services**:
   - Deploy the same codebase twice
   - Configure different environment variables for each
   - Each gets its own domain/URL

## Troubleshooting

### "Both instances using same account"
- Make sure you're using different API keys for paper vs live
- Check that `base_url` is correctly set in your requests

### "Rate limit errors"
- Paper and live share rate limits if same account
- Consider using separate Alpaca accounts

### "Can't start both simultaneously"
- Make sure you're using different API keys
- Check that both requests have different `base_url` values
- Verify your Alpaca account supports both paper and live trading

## Example: Running Both Simultaneously

```bash
# Terminal 1: Start paper trading
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["QQQ"],
    "broker_type": "alpaca",
    "api_key": "PAPER_KEY",
    "api_secret": "PAPER_SECRET",
    "base_url": "https://paper-api.alpaca.markets"
  }'

# Terminal 2: Start live trading (different symbols or same)
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["SPY"],
    "broker_type": "alpaca",
    "api_key": "LIVE_KEY",
    "api_secret": "LIVE_SECRET",
    "base_url": "https://api.alpaca.markets"
  }'
```

**Note:** The current implementation allows one active trading session at a time per server instance. To run both truly simultaneously, use Method 3 (two separate server instances on different ports).

