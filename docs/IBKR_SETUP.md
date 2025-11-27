# Interactive Brokers (IBKR) Setup Guide

This guide explains how to set up and use Interactive Brokers with FutBot.

## Prerequisites

1. **IBKR Account**: You need an Interactive Brokers account (paper or live)
2. **TWS or IB Gateway**: Install Trader Workstation (TWS) or IB Gateway
3. **Python Package**: `ib_insync` is already installed in the project

## Installation Steps

### 1. Install TWS or IB Gateway

**Option A: Trader Workstation (TWS)**
- Download from: https://www.interactivebrokers.com/en/index.php?f=16042
- Install and launch TWS

**Option B: IB Gateway (Lightweight)**
- Download from: https://www.interactivebrokers.com/en/index.php?f=16457
- Install and launch IB Gateway

### 2. Configure API Settings

1. **Enable API Access**:
   - In TWS/Gateway: `Configure` → `API` → `Settings`
   - Check "Enable ActiveX and Socket Clients"
   - Check "Read-Only API" if you want read-only access
   - Set "Socket port" to:
     - **7497** for paper trading
     - **7496** for live trading

2. **Trusted IPs** (Optional but recommended):
   - Add `127.0.0.1` to trusted IPs for local connections
   - For remote connections, add your server's IP

3. **Master API Client ID**:
   - Set a master client ID (default: 0)
   - Your bot will use a different client ID (default: 1)

### 3. Start TWS/IB Gateway

- **Paper Trading**: Start TWS/Gateway and log in with paper trading credentials
- **Live Trading**: Start TWS/Gateway and log in with live account credentials

**Important**: TWS/Gateway must be running before starting FutBot.

## Using IBKR with FutBot

### Via FastAPI

```bash
# Start the API server
python main.py --mode api --port 8000

# Start live trading with IBKR
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["QQQ"],
    "broker_type": "ibkr",
    "ibkr_host": "127.0.0.1",
    "ibkr_port": 7497,
    "ibkr_client_id": 1,
    "ibkr_account_id": null
  }'
```

### Connection Parameters

- **ibkr_host**: TWS/Gateway host (default: `127.0.0.1` for local)
- **ibkr_port**: 
  - `7497` for paper trading
  - `7496` for live trading
- **ibkr_client_id**: Unique client ID (default: `1`)
- **ibkr_account_id**: Specific account ID (optional, uses first account if not specified)

### Programmatically

```python
from core.live import IBKRBrokerClient

# Create client
broker = IBKRBrokerClient(
    host="127.0.0.1",
    port=7497,  # Paper trading
    client_id=1,
    account_id=None  # Uses first account
)

# Connect
if broker.connect():
    print("Connected to IBKR!")
    
    # Get account info
    account = broker.get_account()
    print(f"Cash: ${account.cash}")
    print(f"Equity: ${account.equity}")
    
    # Get positions
    positions = broker.get_positions()
    for pos in positions:
        print(f"{pos.symbol}: {pos.quantity} @ ${pos.avg_entry_price}")
```

## Supported Features

### Order Types
- ✅ Market orders
- ✅ Limit orders
- ✅ Stop orders
- ✅ Time in force: DAY, GTC, IOC, FOK

### Account Management
- ✅ Get account balance
- ✅ Get buying power
- ✅ Get portfolio value

### Position Management
- ✅ Get current positions
- ✅ Get position PnL
- ✅ Real-time position updates

### Order Management
- ✅ Submit orders
- ✅ Get open orders
- ✅ Cancel orders
- ✅ Get order fills

## Troubleshooting

### Connection Issues

**Error: "Failed to connect to IBKR"**
- Ensure TWS/IB Gateway is running
- Check that API is enabled in TWS/Gateway settings
- Verify port number (7497 for paper, 7496 for live)
- Check firewall settings
- Ensure client_id is unique (not used by another connection)

**Error: "Connection refused"**
- TWS/Gateway may not be running
- Port may be incorrect
- API may not be enabled in TWS/Gateway

### Order Issues

**Error: "Order rejected"**
- Check account permissions
- Verify sufficient buying power
- Check market hours (orders may be rejected outside trading hours)
- Verify symbol is valid and tradeable

**Error: "Invalid contract"**
- Symbol may not be valid
- Contract may need additional specifications (exchange, currency)
- Check symbol format (e.g., "QQQ" not "QQQ.US")

### Data Issues

**No market data**
- Ensure market data subscriptions are active in IBKR account
- Check that market data permissions are enabled
- Verify symbol has market data available

## Security Best Practices

1. **Use Paper Trading First**: Always test with paper trading before live
2. **Read-Only API**: Consider using read-only API during testing
3. **Client ID Isolation**: Use unique client IDs for different connections
4. **Account ID**: Specify account_id explicitly for multi-account setups
5. **Firewall**: Restrict API access to trusted IPs only
6. **Kill Switch**: Always have kill switch enabled for live trading

## Paper Trading vs Live Trading

### Paper Trading (Port 7497)
- Uses simulated account
- No real money at risk
- Perfect for testing and development
- Same API interface as live

### Live Trading (Port 7496)
- Uses real account
- Real money at risk
- Requires careful risk management
- Use safe_live_config.yaml settings

## Next Steps

1. **Test Connection**: Verify you can connect to IBKR
2. **Paper Trade**: Run paper trading for 2-4 weeks
3. **Monitor Logs**: Check `logs/trading_events.jsonl` for events
4. **Review Performance**: Use `/stats` and `/visualizations` endpoints
5. **Go Live**: Only after successful paper trading period

## Additional Resources

- IBKR API Documentation: https://interactivebrokers.github.io/tws-api/
- ib_insync Documentation: https://ib-insync.readthedocs.io/
- IBKR Support: https://www.interactivebrokers.com/en/index.php?f=16042

