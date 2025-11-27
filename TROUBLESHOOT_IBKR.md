# IBKR Connection Troubleshooting

## Quick Checklist

If connection is failing, check these in order:

### 1. ✅ IB Gateway is Running
- IB Gateway window should be open and logged in
- You should see "Connected" status in IB Gateway

### 2. ✅ API is Enabled
In IB Gateway:
- Go to: **Configure** → **API** → **Settings**
- ✅ Check **"Enable ActiveX and Socket Clients"**
- Set **Socket port** to:
  - **7497** for paper trading
  - **7496** for live trading
- Click **OK**

### 3. ✅ Port is Correct
Run this to check which ports are open:
```bash
python scripts/check_ibkr_port.py
```

### 4. ✅ Client ID is Unique
- Each connection needs a unique client ID
- Default is `1`, but if you have other apps connected, use a different number (2, 3, etc.)

### 5. ✅ Trusted IPs (if needed)
- In API Settings, you can add `127.0.0.1` to trusted IPs
- This is optional but can help with connection issues

## Common Issues

### "Connection Refused"
- **Cause**: API not enabled or wrong port
- **Fix**: Enable API in IB Gateway settings, verify port number

### "Connection Timeout"
- **Cause**: Firewall blocking or IB Gateway not running
- **Fix**: Check firewall, ensure IB Gateway is running

### "Order Rejected"
- **Cause**: Not a connection issue - this is normal if:
  - Market is closed
  - Insufficient buying power
  - Invalid symbol
  - Account restrictions

## Testing Connection

```bash
# Check which ports are open
python scripts/check_ibkr_port.py

# Test full connection
python scripts/check_ibkr_connection.py
```

## Manual Port Check

If you want to manually check the port:
```bash
# Check if port 7497 is open
nc -zv 127.0.0.1 7497

# Or use telnet
telnet 127.0.0.1 7497
```

## Still Not Working?

1. **Restart IB Gateway** after changing API settings
2. **Check IB Gateway logs** for error messages
3. **Try a different client ID** (2, 3, 4, etc.)
4. **Verify Java is working**: `java -version`
5. **Check system firewall** isn't blocking the port

## Success Indicators

When everything is working:
- `check_ibkr_port.py` shows port is OPEN
- `check_ibkr_connection.py` shows account balance
- No connection errors in logs

