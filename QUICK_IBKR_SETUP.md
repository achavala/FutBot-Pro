# Quick IBKR Setup Guide

The easiest way to get IBKR working with FutBot.

## Option 1: IB Gateway (Recommended - Lighter)

**IB Gateway** is a lightweight version of TWS, perfect for API-only trading.

### Step 1: Install Java (if needed)
```bash
# macOS
brew install openjdk

# Or download from: https://www.java.com/download/
```

### Step 2: Download IB Gateway
1. Go to: https://www.interactivebrokers.com/en/index.php?f=16457
2. Download IB Gateway for your OS
3. Install it

### Step 3: Run Setup Script
```bash
cd /Users/chavala/FutBot
source .venv/bin/activate
./scripts/setup_ibkr.sh
```

### Step 4: Launch IB Gateway
1. Open IB Gateway
2. Log in with your IBKR account (paper or live)
3. **Important**: Keep IB Gateway running while using FutBot

### Step 5: Configure API
1. In IB Gateway: `Configure` → `API` → `Settings`
2. ✅ Check "Enable ActiveX and Socket Clients"
3. Set Socket port:
   - **7497** for paper trading
   - **7496** for live trading
4. (Optional) Add `127.0.0.1` to trusted IPs
5. Click "OK"

### Step 6: Test Connection
```bash
python scripts/check_ibkr_connection.py
```

If successful, you'll see your account balance and positions.

### Step 7: Start Trading
```bash
# Start API server
python main.py --mode api --port 8000

# In another terminal or via API client:
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["QQQ"],
    "broker_type": "ibkr",
    "ibkr_host": "127.0.0.1",
    "ibkr_port": 7497,
    "ibkr_client_id": 1
  }'
```

## Option 2: TWS (Full Trading Platform)

If you prefer the full Trader Workstation:

1. Download from: https://www.interactivebrokers.com/en/index.php?f=16042
2. Install and launch TWS
3. Follow steps 4-7 above (same API configuration)

## Troubleshooting

### "Failed to connect"
- ✅ Ensure IB Gateway/TWS is running
- ✅ Check API is enabled in settings
- ✅ Verify port number (7497 paper, 7496 live)
- ✅ Try restarting IB Gateway/TWS

### "Connection refused"
- Check firewall isn't blocking the port
- Verify you're using the correct port
- Ensure no other application is using that port

### "Order rejected"
- Check account has sufficient buying power
- Verify market is open (orders may be rejected outside hours)
- Check symbol is valid and tradeable

## Quick Test

Run this to verify everything works:
```bash
python scripts/check_ibkr_connection.py
```

You should see:
```
✅ Connected to Paper Trading!
Account Information:
  Cash: $XXX,XXX.XX
  Equity: $XXX,XXX.XX
  Buying Power: $XXX,XXX.XX
```

## Next Steps

Once connected:
1. Start with **paper trading** (port 7497)
2. Monitor for 2-4 weeks using `BURN_IN_CHECKLIST.md`
3. Only switch to live (port 7496) after successful paper trading

## Need Help?

- Full documentation: `docs/IBKR_SETUP.md`
- IBKR Support: https://www.interactivebrokers.com/en/index.php?f=16042
- ib_insync docs: https://ib-insync.readthedocs.io/

