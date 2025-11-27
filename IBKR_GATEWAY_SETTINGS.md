# IB Gateway API Settings (Correct Settings)

## Important: IB Gateway vs TWS

**IB Gateway**: "Enable ActiveX and Socket Clients" is **enabled by default** and not visible in the UI.

**TWS**: You must manually enable "Enable ActiveX and Socket Clients".

## IB Gateway Settings to Check

### 1. API Settings (Configure → API → Settings)

✅ **Socket port**: Should be `4002` (or whatever port you're using)
✅ **Read-Only API**: Should be **UNCHECKED** (you already did this)
✅ **Trusted IPs**: Should include `127.0.0.1` (you already have this)

### 2. API Precautions (Configure → API → Precautions) ⚠️ CRITICAL

This is often the issue! Go to:
- **Configure** → **API** → **Precautions**

**Enable ALL checkboxes** to bypass order precautions:
- ✅ Bypass order precautions for API orders
- ✅ (Any other precaution checkboxes)

**Why this matters**: If precautions are enabled, IB Gateway may block or timeout API connections even if the port is open.

### 3. Verify Connection

After enabling precautions:
1. **Restart IB Gateway** (close and reopen)
2. Log back in
3. Test connection:

```bash
python scripts/diagnose_ibkr.py
```

## Complete Checklist

- [ ] Socket port set to 4002
- [ ] Read-Only API is **unchecked**
- [ ] Trusted IPs includes 127.0.0.1
- [ ] **API Precautions: All checkboxes enabled** ⚠️
- [ ] IB Gateway restarted after changes
- [ ] IB Gateway is fully connected (see account updates in logs)

## If Still Not Working

1. **Check IB Gateway Logs** for API connection attempts
2. **Try a different client ID** (2, 3, 4, etc.)
3. **Check firewall** isn't blocking
4. **Try TWS instead** of IB Gateway (sometimes works better)

## Testing

```bash
# Test connection
python scripts/diagnose_ibkr.py

# Or direct test
python -c "
from ib_insync import IB
ib = IB()
ib.connect('127.0.0.1', 4002, clientId=3, timeout=15)
print('Connected!')
print('Accounts:', ib.managedAccounts())
ib.disconnect()
"
```

