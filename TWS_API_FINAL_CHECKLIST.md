# TWS API Connection - Final Checklist

## ✅ Already Verified
- ✅ Port 7497 is OPEN and accepting TCP connections
- ✅ "Enable ActiveX and Socket Clients" is CHECKED
- ✅ Socket port is set to 7497
- ✅ "Read-Only API" is UNCHECKED
- ✅ All API Precautions are enabled
- ✅ TWS has been restarted

## 🔍 Critical: Trusted IPs (MOST LIKELY ISSUE)

In TWS: **Configure → API → Settings**

Look carefully for:
1. **"Trusted IPs"** field (might be at the bottom or in a separate section)
2. **"Allow connections from localhost only"** checkbox
3. **"Trusted IPs"** list/table

**If you see Trusted IPs:**
- Click "Add" or "+" button
- Enter: `127.0.0.1`
- Click "OK" (NOT just "Apply")
- **RESTART TWS**

**If you DON'T see Trusted IPs:**
- Some TWS versions hide it if empty
- Try scrolling down in the API Settings window
- Check if there's an "Advanced" or "Security" tab

## ⚠️ Important: Saving Settings

When you make changes in TWS:
1. Click **"Apply"** first (if available)
2. Then click **"OK"**
3. **RESTART TWS** (close completely, reopen)
4. Wait for TWS to fully connect

## Alternative: Check TWS API Logs

TWS creates API log files. To find them:

1. In TWS, go to: **Help → API Logs** (if available)
2. Or check: `~/Library/Application Support/TWS/` or `~/Library/Application Support/IB Gateway/`
3. Look for files named `api.log` or similar
4. Check for connection attempts and error messages

## Test After Each Change

After making any change:
```bash
source .venv/bin/activate
python scripts/check_ibkr_api.py
```

## If Still Not Working

1. **Try IB Gateway instead of TWS**:
   - IB Gateway is lighter and sometimes works better for API
   - Download from IBKR website
   - Use port 4002 for paper trading

2. **Check macOS Firewall**:
   - System Settings → Network → Firewall
   - Make sure TWS is allowed
   - Or temporarily disable to test

3. **Try different port**:
   - In TWS, change socket port to 4002
   - Restart TWS
   - Test with port 4002

4. **Contact IBKR Support**:
   - They can check your account settings
   - May have server-side restrictions

## Current Status

- TCP connection: ✅ Working
- API handshake: ❌ Timing out
- Most likely cause: Trusted IPs not configured

