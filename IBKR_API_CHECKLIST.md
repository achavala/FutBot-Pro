# IBKR API Setup Checklist

## ✅ Step-by-Step API Configuration

### 1. Open IB Gateway Settings
- In IB Gateway, go to: **Configure** → **API** → **Settings**

### 2. Enable API Access
- ✅ Check **"Enable ActiveX and Socket Clients"**
- This is the most important setting!

### 3. Set Socket Port
- Set **Socket port** to one of:
  - **4002** (default TWS/Gateway port)
  - **7497** (paper trading)
  - **7496** (live trading)
- **Note**: The port you set here must match what you use in FutBot

### 4. Trusted IPs (Optional but Recommended)
- Add **127.0.0.1** to trusted IPs
- This allows local connections

### 5. Read-Only API (Optional)
- If you want extra safety during testing, check "Read-Only API"
- This prevents accidental trades

### 6. Save and Restart
- Click **OK** to save settings
- **Restart IB Gateway** (close and reopen)
- This is important - API changes require a restart

### 7. Verify Connection
```bash
python scripts/diagnose_ibkr.py
```

## Common Mistakes

❌ **Forgot to check "Enable ActiveX and Socket Clients"**
- This is the #1 reason connections fail

❌ **Didn't restart IB Gateway after changing settings**
- API settings only take effect after restart

❌ **Wrong port number**
- Check what port you set in IB Gateway
- Use that exact port in FutBot

❌ **Client ID conflict**
- If another app is using client ID 1, use 2, 3, etc.

## Quick Test

After configuring, run:
```bash
python scripts/diagnose_ibkr.py
```

You should see:
```
✅ Port 4002: ✅ OPEN
✅ Successfully connected on port 4002!
💡 Use port 4002 in your connection settings
```

## Still Having Issues?

1. **Check IB Gateway Logs**
   - Look for error messages in IB Gateway
   - Check for API-related warnings

2. **Try Different Client ID**
   - Use client ID 2, 3, or 4 instead of 1

3. **Verify Port in IB Gateway**
   - Go back to API Settings
   - Confirm the port number shown matches what you're using

4. **Check Firewall**
   - macOS firewall might be blocking
   - Try temporarily disabling to test

5. **Restart Everything**
   - Close IB Gateway completely
   - Restart IB Gateway
   - Try connection again

