# 🚀 IBKR Quick Start - 5 Minutes to Trading

## ✅ What's Already Done

Your FutBot is **already configured** for Interactive Brokers:

- ✅ IBKR broker client implemented
- ✅ `.env.local` configured with your account (`U21013024`)
- ✅ `ib-insync` library installed
- ✅ Broker type set to IBKR

**You just need to start IB Gateway!**

---

## 🎯 Step-by-Step (5 Minutes)

### **Step 1: Download IB Gateway (if not installed)**

https://www.interactivebrokers.com/en/trading/ibgateway-stable.php

Choose your OS and install.

---

### **Step 2: Start IB Gateway**

1. **Launch IB Gateway**
2. Select **Paper Trading** (top-left dropdown)
3. Log in with your IBKR credentials
4. Wait for "Connected" status

---

### **Step 3: Enable API**

In IB Gateway:

1. Click **Configure** → **Settings** → **API** → **Settings**
2. Check these boxes:
   - ✅ **Enable ActiveX and Socket Clients**
   - ✅ **Socket port: 7497**
   - ✅ **Trusted IP: 127.0.0.1**
3. Click **OK**

---

### **Step 4: Test Connection**

```bash
python test_ibkr_connection.py
```

You should see:
```
✓ Connected successfully!
✓ Account Information:
  Account ID: U21013024
  Cash: $1,000,000.00
✓ QQQ current price: $596.72
✓ All tests passed!
```

---

### **Step 5: Start Trading Bot**

```bash
python main.py --mode live --symbol QQQ --capital 100000
```

Then open: http://localhost:8000/visualizations/dashboard

---

## 🔧 Your Configuration

From your `.env.local`:

```bash
BROKER_TYPE=ibkr                # Using IBKR
IB_HOST=127.0.0.1               # Localhost
IB_PORT=7497                    # Paper trading (SAFE)
IB_CLIENT_ID=1                  # Client ID
IB_ACCOUNT_ID=U21013024         # Your account
```

---

## ⚠️ Important Notes

### **Paper Trading (Port 7497) - SAFE**
- Virtual money, no risk
- Test strategies safely
- Real market data

### **Live Trading (Port 7496) - DANGEROUS**
- Real money at risk!
- Only after extensive paper testing
- Change port in `.env.local`: `IB_PORT=7496`

**Always use 7497 for testing!**

---

## 🛠️ Troubleshooting

### **"Connection refused"**

**Problem**: IB Gateway not running or wrong port

**Fix**:
```bash
# Check IB Gateway is running and shows port 7497
# Verify API is enabled in Settings
```

### **"No security definition"**

**Problem**: Invalid symbol

**Fix**: Use standard symbols (QQQ, SPY, AAPL)

### **"Not connected"**

**Problem**: IB Gateway disconnected

**Fix**:
1. Restart IB Gateway
2. Restart bot

---

## 📚 Full Documentation

- **Complete setup**: See `IBKR_SETUP.md`
- **API keys**: See `SETUP.md`
- **Visualizations**: See `QUICKSTART.md`

---

## ✨ What You Can Do Now

### **1. Demo Mode (No IB Gateway needed)**
```bash
python main.py --mode api --port 8000 --demo
```

### **2. Paper Trading (Requires IB Gateway)**
```bash
python main.py --mode live --symbol QQQ --capital 100000
```

### **3. Backtest on Real Data**
```bash
python -m backtesting.cli --data data/QQQ_1min_5days.csv --symbol QQQ
```

---

## 🎉 You're Ready!

Your FutBot is configured for IBKR. Just:

1. Start IB Gateway (paper trading mode)
2. Run `python test_ibkr_connection.py` to verify
3. Start the bot: `python main.py --mode live --symbol QQQ`
4. Monitor: http://localhost:8000/visualizations/dashboard

---

**Questions?** Check `IBKR_SETUP.md` for detailed instructions.
