# 🏦 Interactive Brokers Setup Guide

Complete guide to setting up FutBot with Interactive Brokers (IBKR).

---

## 📋 Prerequisites

- Active Interactive Brokers account
- IB Gateway or Trader Workstation (TWS) installed
- Paper trading account enabled (recommended for testing)
- Python environment configured (see SETUP.md)

---

## 🔧 Step 1: Install IB Gateway

### **Download IB Gateway**

1. Go to: https://www.interactivebrokers.com/en/trading/ibgateway-stable.php
2. Download for your OS:
   - **Mac**: IB Gateway (Latest Stable)
   - **Windows**: IB Gateway (Latest Stable)
   - **Linux**: IB Gateway (Latest Stable)

3. Install the application

### **Why IB Gateway vs TWS?**

| IB Gateway | TWS (Trader Workstation) |
|------------|--------------------------|
| Lightweight | Full trading platform |
| Headless (no GUI needed) | Has trading interface |
| Lower resource usage | Higher resource usage |
| **Recommended for bots** | Good for manual trading |

---

## 🔑 Step 2: Configure Paper Trading Account

### **Enable Paper Trading**

1. Log in to your IBKR account portal: https://www.interactivebrokers.com/sso/Login
2. Navigate to **Account Management**
3. Go to **Settings** → **Paper Trading**
4. Click **Enable Paper Trading Account**
5. Note your paper trading account ID (format: DU######)

Your account ID from `.env.local`: **U21013024**

### **Set Up Permissions**

1. In Account Management, go to **Settings** → **API** → **Settings**
2. Enable the following:
   - ✅ **Enable ActiveX and Socket Clients**
   - ✅ **Read-Only API** (uncheck for trading)
   - ✅ **Download open orders on connection**
   - ✅ **Allow connections from localhost**

3. Add **Trusted IP Addresses**:
   - Add `127.0.0.1` (localhost)
   - This allows your bot to connect

---

## 🚀 Step 3: Start IB Gateway

### **Launch IB Gateway**

1. Open IB Gateway application
2. Select **Paper Trading** mode (top-left dropdown)
3. Enter your IBKR credentials
4. Check "Store settings on server" for convenience
5. Click **Login**

### **Configure Connection Settings**

After login, go to **Configure** → **Settings** → **API** → **Settings**:

```
✅ Enable ActiveX and Socket Clients
✅ Socket port: 7497 (paper) or 7496 (live)
✅ Trusted IP addresses: 127.0.0.1
✅ Create API message log file: [optional, for debugging]
```

Click **OK** to save.

### **Verify IB Gateway is Running**

You should see:
- Status: **Connected**
- Port: **7497** (paper) or **7496** (live)
- Green indicator in system tray

---

## ⚙️ Step 4: Configure FutBot

Your `.env.local` is already configured:

```bash
# PRIMARY BROKER: Interactive Brokers
BROKER_TYPE=ibkr

# Interactive Brokers Configuration
IB_HOST=127.0.0.1
IB_PORT=7497              # 7497 for paper, 7496 for live
IB_CLIENT_ID=1
IB_ACCOUNT_ID=U21013024   # Your account ID
```

### **Port Configuration**

| Mode | Port | When to Use |
|------|------|-------------|
| **7497** | Paper Trading | Testing, development (SAFE) |
| **7496** | Live Trading | Real money (DANGEROUS) |

**Always use port 7497 for paper trading!**

---

## 🧪 Step 5: Test Connection

### **Test Script**

Run this to verify your IBKR connection:

```bash
python test_ibkr_connection.py
```

You should see:

```
============================================================
Testing IBKR Connection
============================================================

Connecting to IB Gateway at 127.0.0.1:7497...
✓ Connected successfully!

Account Information:
  Account ID: U21013024
  Cash: $1,000,000.00
  Equity: $1,000,000.00
  Buying Power: $4,000,000.00

Testing market data...
✓ QQQ current price: $596.72

Testing order submission (paper trade)...
✓ Order submitted: BUY 1 QQQ at market
  Order ID: 123456
  Status: Submitted

✓ All tests passed!
============================================================
```

---

## 🎯 Step 6: Run FutBot with IBKR

### **Start the Bot**

```bash
# Demo mode (no IB Gateway needed)
python main.py --mode api --port 8000 --demo

# Live paper trading (requires IB Gateway running)
python main.py --mode live --symbol QQQ --capital 100000
```

### **Monitor Trading**

Open these in your browser:

1. **Dashboard**: http://localhost:8000/visualizations/dashboard
2. **API Docs**: http://localhost:8000/docs
3. **Health Check**: http://localhost:8000/health
4. **Open Orders**: http://localhost:8000/broker/orders

---

## 🔍 Troubleshooting

### **Error: "Connection refused"**

**Cause**: IB Gateway is not running or wrong port

**Fix**:
1. Open IB Gateway
2. Verify you're logged in
3. Check the port matches (7497 for paper)
4. Check `.env.local` has correct `IB_PORT`

```bash
# Check if port is listening
lsof -i :7497
```

### **Error: "No security definition found"**

**Cause**: Invalid ticker symbol

**Fix**:
- Use standard symbols: QQQ, SPY, AAPL (not Q, ESZ4, etc.)
- Check symbol exists on IBKR

### **Error: "Not connected to TWS/Gateway"**

**Cause**: IB Gateway closed connection

**Fix**:
1. Restart IB Gateway
2. Restart FutBot
3. Check firewall isn't blocking port 7497

### **Error: "Order rejected: insufficient funds"**

**Cause**: Position size exceeds buying power

**Fix**:
```bash
# In .env.local, reduce position size
MAX_POSITION_SIZE_PCT=0.05  # 5% instead of 10%
```

### **IB Gateway keeps disconnecting**

**Cause**: Auto-logout enabled

**Fix**:
1. In IB Gateway: **File** → **Global Configuration** → **Lock and Exit**
2. Set **Auto logout** to higher value or uncheck
3. Enable **Keep connection alive**

---

## 📊 Paper vs Live Trading

### **Paper Trading (Port 7497) - SAFE**

```bash
IB_PORT=7497
IB_ACCOUNT_ID=DU21013024  # Note: DU prefix for paper
```

**Benefits:**
- ✅ No real money at risk
- ✅ Test strategies safely
- ✅ Same market data as live
- ✅ Practice order execution
- ✅ Unlimited virtual capital

**Limitations:**
- ⚠️ Fills may be more optimistic
- ⚠️ No slippage in some cases
- ⚠️ Market impact not simulated

### **Live Trading (Port 7496) - DANGEROUS**

```bash
IB_PORT=7496
IB_ACCOUNT_ID=U21013024  # Note: U prefix for live
```

**Requirements:**
- ✅ Funded account
- ✅ Tested thoroughly in paper mode
- ✅ Risk limits configured
- ✅ Monitoring in place
- ✅ Stop-loss strategy

**⚠️ WARNING: Live trading risks real money!**

---

## 🛡️ Safety Checklist

Before going live:

- [ ] Tested in paper mode for at least 1 week
- [ ] Observed drawdowns and verified acceptable
- [ ] Risk limits configured (`MAX_DAILY_LOSS_PCT`, `MAX_LOSS_STREAK`)
- [ ] Position sizing is conservative (`MAX_POSITION_SIZE_PCT ≤ 0.05`)
- [ ] Kill switch tested and working
- [ ] Monitoring dashboard accessible
- [ ] Alerts configured (Slack/Email/SMS)
- [ ] Emergency contact plan in place
- [ ] Only trading capital you can afford to lose

---

## 📚 Useful IB Gateway Settings

### **Recommended Settings**

```
API → Settings:
  ✅ Enable ActiveX and Socket Clients
  ✅ Socket port: 7497 (paper) / 7496 (live)
  ✅ Master API client ID: 0
  ✅ Read-Only API: ❌ (need to place orders)
  ✅ Download open orders on connection
  ✅ Allow connections from: localhost (127.0.0.1)

Lock and Exit:
  ❌ Auto logout time: Disabled
  ✅ Re-login automatically

General:
  ❌ Show startup tips
  ✅ Minimize to system tray
  ✅ Start on Windows startup (optional)
```

### **Multiple Connections**

You can run multiple bots simultaneously:

```bash
# Bot 1
IB_CLIENT_ID=1

# Bot 2
IB_CLIENT_ID=2

# Bot 3
IB_CLIENT_ID=3
```

Each needs a unique `CLIENT_ID` in `.env.local`.

---

## 🔧 Advanced Configuration

### **IB Gateway API Settings**

Edit: `~/.ibgateway/config.ini` (Mac/Linux) or `C:\Users\{user}\.ibgateway\config.ini` (Windows)

```ini
[API]
enableapi=yes
socketport=7497
masterClientID=0
readonly=no

[Logon]
autologon=yes
username=your_username
save_password=yes
```

### **Docker Deployment (Optional)**

Run IB Gateway in Docker for isolated environment:

```dockerfile
FROM ghcr.io/ib-controller/ib-gateway-docker:latest

ENV TWS_USERID="your_username"
ENV TWS_PASSWORD="your_password"
ENV TRADING_MODE="paper"
ENV TWOFA_TIMEOUT_ACTION="restart"
```

---

## 📞 Support

### **IBKR Support**

- **Phone**: 1-877-442-2757 (US)
- **Web**: https://www.interactivebrokers.com/en/support.php
- **Chat**: Available in account portal

### **IB Gateway Issues**

- Official docs: https://www.interactivebrokers.com/en/trading/ibgateway-latest.php
- API reference: https://interactivebrokers.github.io/tws-api/

### **FutBot Issues**

- Check logs: `logs/futbot.log`
- Review API docs: http://localhost:8000/docs
- Test connection: `python test_ibkr_connection.py`

---

## ✅ Quick Start Checklist

1. [ ] Install IB Gateway
2. [ ] Enable paper trading in IBKR account
3. [ ] Configure API permissions
4. [ ] Start IB Gateway (port 7497)
5. [ ] Update `.env.local` with account ID
6. [ ] Install `ib-insync`: `pip install ib-insync`
7. [ ] Test connection: `python test_ibkr_connection.py`
8. [ ] Start FutBot: `python main.py --mode live`
9. [ ] Monitor dashboard: http://localhost:8000/visualizations/dashboard

---

**Remember**: Always test in paper mode before risking real money!
