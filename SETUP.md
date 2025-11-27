# 🔧 Setup Guide - Getting Started with API Keys

This guide will help you set up FutBot for live trading or paper trading.

## 📋 Prerequisites

- Python 3.10 or higher
- Virtual environment activated
- Basic understanding of trading concepts

---

## 🔑 Step 1: Get Your API Keys

### **Option A: Polygon.io (Recommended for Data)**

1. Go to https://polygon.io/
2. Sign up for an account
3. Choose a plan:
   - **Free**: 5 API calls/minute, delayed data (good for testing)
   - **Starter ($29/mo)**: Real-time data, unlimited calls (recommended for live trading)
4. Copy your API key from the dashboard

### **Option B: Alpaca (Recommended for Broker)**

1. Go to https://alpaca.markets/
2. Sign up for a free paper trading account
3. Navigate to your paper trading dashboard: https://app.alpaca.markets/paper/dashboard/overview
4. Go to "Your API Keys" section
5. Generate new keys (you'll get both API key and secret key)
6. Copy both keys

**Important**:
- Use paper trading URL: `https://paper-api.alpaca.markets`
- Test thoroughly before switching to live trading
- Live trading URL: `https://api.alpaca.markets`

### **Option C: Finnhub (Optional - for News Sentiment)**

1. Go to https://finnhub.io/
2. Sign up for free account
3. Copy API key from dashboard
4. Free tier: 60 calls/minute

---

## 🛠️ Step 2: Install Dependencies

```bash
# Activate virtual environment
source .venv/bin/activate

# Install all dependencies
pip install -r requirements.txt

# Or install core dependencies only
pip install numpy pandas scipy statsmodels scikit-learn matplotlib plotly fastapi uvicorn pydantic pyyaml python-dotenv pytest polygon-api-client alpaca-py
```

---

## ⚙️ Step 3: Configure Environment Variables

### **Create Your .env File**

```bash
# Copy the example file
cp .env.example .env

# Open in your editor
nano .env  # or vim, code, etc.
```

### **Minimal Configuration (Paper Trading)**

Edit `.env` and add at minimum:

```bash
# Data provider
POLYGON_API_KEY=your_actual_polygon_key_here

# Broker (paper trading)
ALPACA_API_KEY=your_actual_alpaca_key_here
ALPACA_SECRET_KEY=your_actual_alpaca_secret_here
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Trading config
TRADING_SYMBOL=QQQ
INITIAL_CAPITAL=100000.0
TRADING_MODE=paper

# Risk limits
MAX_DAILY_LOSS_PCT=0.02
MAX_LOSS_STREAK=5
MAX_POSITION_SIZE_PCT=0.10

# Logging
LOG_LEVEL=INFO
LOG_TO_FILE=true
```

### **Verify Your Configuration**

```bash
# Check that .env is loaded correctly
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('Polygon key:', os.getenv('POLYGON_API_KEY')[:10] + '...')"
```

---

## 🧪 Step 4: Test Your API Keys

### **Test Polygon.io Connection**

```bash
python << EOF
import os
from dotenv import load_dotenv
from polygon import RESTClient

load_dotenv()
api_key = os.getenv('POLYGON_API_KEY')

client = RESTClient(api_key)
try:
    # Get latest quote for QQQ
    quote = client.get_last_quote('QQQ')
    print(f"✓ Polygon.io connected successfully!")
    print(f"  QQQ Last Price: \${quote.bid_price}")
except Exception as e:
    print(f"✗ Error connecting to Polygon: {e}")
EOF
```

### **Test Alpaca Connection**

```bash
python << EOF
import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient

load_dotenv()
api_key = os.getenv('ALPACA_API_KEY')
secret_key = os.getenv('ALPACA_SECRET_KEY')

try:
    client = TradingClient(api_key, secret_key, paper=True)
    account = client.get_account()
    print(f"✓ Alpaca connected successfully!")
    print(f"  Account: {account.account_number}")
    print(f"  Buying Power: \${float(account.buying_power):,.2f}")
    print(f"  Cash: \${float(account.cash):,.2f}")
except Exception as e:
    print(f"✗ Error connecting to Alpaca: {e}")
EOF
```

---

## 🚀 Step 5: Start the Bot

### **Demo Mode (No API Keys Required)**

```bash
python main.py --mode api --port 8000 --demo
```

Then open: http://localhost:8000/visualizations/dashboard

### **Paper Trading Mode**

```bash
python main.py --mode live --symbol QQQ --capital 100000
```

### **Backtest Mode**

```bash
# First, download some data
python -m services.polygon_client --symbol QQQ --start 2024-01-01 --end 2024-03-31 --output data/QQQ_1min.csv

# Run backtest
python -m backtesting.cli --data data/QQQ_1min.csv --start 2024-01-01 --end 2024-03-31
```

---

## 📊 Step 6: Monitor the Bot

### **Web Interface**

```
http://localhost:8000/docs           # API documentation
http://localhost:8000/health          # Health check
http://localhost:8000/visualizations/dashboard  # Performance dashboard
```

### **Command Line**

```bash
# Check bot status
curl http://localhost:8000/health | python -m json.tool

# Get current regime
curl http://localhost:8000/regime | python -m json.tool

# Get portfolio stats
curl http://localhost:8000/stats | python -m json.tool
```

---

## 🔒 Security Best Practices

### **1. Never Commit .env File**

```bash
# Check .gitignore includes .env
grep "^\.env$" .gitignore

# If not, add it
echo ".env" >> .gitignore
```

### **2. Use Paper Trading First**

- **Always test with paper trading** before going live
- Run for at least 1 week in paper mode
- Monitor for bugs, unexpected behavior, drawdowns

### **3. Set Strict Risk Limits**

```bash
# In .env, set conservative limits
MAX_DAILY_LOSS_PCT=0.01  # 1% max daily loss
MAX_POSITION_SIZE_PCT=0.05  # 5% max position
MIN_CONFIDENCE_THRESHOLD=0.6  # Higher confidence required
```

### **4. Enable Alerts**

Set up Slack or email alerts for:
- Large losses
- Kill switch engagement
- API connection errors
- Unusual behavior

---

## 🛠️ Troubleshooting

### **Error: "ModuleNotFoundError: No module named 'polygon'"**

```bash
pip install polygon-api-client
```

### **Error: "Invalid API key"**

- Check that you copied the entire key (no spaces)
- Verify key is active in Polygon/Alpaca dashboard
- Check you're using the right URL (paper vs live)

### **Error: "Rate limit exceeded"**

- Free tier has limits (5 calls/min for Polygon)
- Upgrade to paid tier
- Or increase polling interval in config

### **Error: "Market is closed"**

- Check trading hours: 9:30 AM - 4:00 PM ET (14:30-21:00 UTC)
- Bot won't trade outside market hours
- Use `DEBUG_MODE=true` to test outside hours

---

## 📚 Next Steps

Once everything is working:

1. **Run backtests** on historical data to validate strategies
2. **Paper trade for 1-2 weeks** to ensure stability
3. **Monitor visualizations** to understand system behavior
4. **Fine-tune risk parameters** based on results
5. **Consider live trading** only after extensive testing

---

## 💡 Tips

- **Start small**: Use conservative position sizes initially
- **Monitor daily**: Check the dashboard at least once per day
- **Keep logs**: Enable file logging for debugging
- **Set alerts**: Get notified of important events
- **Backup state**: Regularly backup `data/` and `config/` directories

---

## 🆘 Need Help?

- Check logs in `logs/futbot.log`
- Review the QUICKSTART.md for usage examples
- Check API documentation: http://localhost:8000/docs
- Report issues on GitHub (if applicable)

---

**Remember**: This is a trading bot that uses real money in live mode. Test thoroughly and never risk more than you can afford to lose.
