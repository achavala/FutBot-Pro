# Alpaca Quick Start Guide

## Setup

### 1. Get Alpaca API Keys

1. Sign up at https://alpaca.markets/
2. Go to your paper trading dashboard: https://app.alpaca.markets/paper/dashboard/overview
3. Navigate to: **Your Account** → **API Keys**
4. Generate API keys (or use existing ones)
5. Copy your **API Key ID** and **Secret Key**

### 2. Set Environment Variables

Add to your `.env` file or export:

```bash
export ALPACA_API_KEY="your_api_key_here"
export ALPACA_SECRET_KEY="your_secret_key_here"
export ALPACA_BASE_URL="https://paper-api.alpaca.markets"  # Paper trading
# For live trading, use: https://api.alpaca.markets
```

### 3. Install Dependencies

```bash
pip install alpaca-py
```

## Starting Live Trading with Alpaca

### Option 1: Using Environment Variables

```bash
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["QQQ"],
    "broker_type": "alpaca"
  }'
```

### Option 2: Providing Credentials in Request

```bash
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["QQQ"],
    "broker_type": "alpaca",
    "api_key": "your_api_key",
    "api_secret": "your_secret_key"
  }'
```

## Advantages of Alpaca

✅ **Simple REST API** - No complex socket connections  
✅ **No local software** - No need for TWS/IB Gateway  
✅ **Fast setup** - Just API keys  
✅ **Reliable** - Cloud-based, always available  
✅ **Paper trading** - Free paper trading account  

## Testing Connection

Test your Alpaca connection:

```bash
python -c "
from alpaca.trading.client import TradingClient
import os

api_key = os.getenv('ALPACA_API_KEY')
secret_key = os.getenv('ALPACA_SECRET_KEY')

if api_key and secret_key:
    client = TradingClient(api_key, secret_key, paper=True)
    account = client.get_account()
    print(f'✅ Connected! Account: {account.account_number}')
    print(f'   Cash: ${float(account.cash):,.2f}')
    print(f'   Equity: ${float(account.equity):,.2f}')
else:
    print('❌ API keys not set')
"
```

## Monitoring

Check bot status:

```bash
curl http://localhost:8000/live/status
curl http://localhost:8000/stats
curl http://localhost:8000/risk-status
```

## Next Steps

1. ✅ Get Alpaca API keys
2. ✅ Set environment variables
3. ✅ Start live trading
4. ✅ Monitor performance

Enjoy trading with Alpaca! 🚀

