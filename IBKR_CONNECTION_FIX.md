# IBKR Connection Fix

## Current Status

✅ IB Gateway is running and connected
✅ Account DUM621028 is active
✅ Port 4002 is open
❌ API connection is timing out

## The Issue

The port is open, but the API connection times out. This usually means:
- The API socket server isn't fully enabled
- There's a client ID conflict
- The connection needs more time to establish

## Solution Steps

### 1. Verify API Settings in IB Gateway

Go to: **Configure** → **API** → **Settings**

**Critical Checkbox:**
- ✅ **"Enable ActiveX and Socket Clients"** MUST be checked
- This is different from just having the port open

**If it's not checked:**
1. Check the box
2. Click **OK**
3. **Restart IB Gateway completely** (close and reopen)
4. Log back in
5. Wait for it to fully connect (you'll see account updates in logs)

### 2. Try Different Client IDs

If client ID 1 is in use, try:
- Client ID 2
- Client ID 3
- Client ID 4

Each connection needs a unique client ID.

### 3. Test Connection

After restarting IB Gateway with API enabled:

```bash
python scripts/diagnose_ibkr.py
```

Or test directly:
```bash
python -c "
from ib_insync import IB
ib = IB()
ib.connect('127.0.0.1', 4002, clientId=3, timeout=15)
print('Connected!')
accounts = ib.managedAccounts()
print(f'Accounts: {accounts}')
ib.disconnect()
"
```

### 4. Start FutBot

Once connection works, use:

```bash
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["QQQ"],
    "broker_type": "ibkr",
    "ibkr_host": "127.0.0.1",
    "ibkr_port": 4002,
    "ibkr_client_id": 3
  }'
```

## Common Mistakes

❌ **Port is open but API not enabled**
- Port 4002 being open doesn't mean API is enabled
- You MUST check "Enable ActiveX and Socket Clients"

❌ **Didn't restart after enabling API**
- API settings only take effect after restart
- Close IB Gateway completely, then reopen

❌ **Client ID conflict**
- If another app is using client ID 1, use 2, 3, or 4
- Each connection needs a unique ID

## Verification

When everything is working:
- `diagnose_ibkr.py` shows "Successfully connected"
- You can see account information
- No timeout errors

## Still Not Working?

1. **Check IB Gateway Logs** for API-related errors
2. **Try TWS instead of IB Gateway** (sometimes TWS works better)
3. **Check firewall** isn't blocking connections
4. **Verify Java version**: `java -version` should work
5. **Update ib_insync**: `pip install --upgrade ib-insync`

