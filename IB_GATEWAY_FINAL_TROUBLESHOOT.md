# IB Gateway Connection - Final Troubleshooting

## Current Status
- ✅ IB Gateway is running (process 30570)
- ✅ Port 4002 is OPEN
- ✅ All settings appear correct
- ❌ API handshake timing out / connection reset

## Mixed Errors Observed
- `TimeoutError` - API handshake not completing
- `Connection reset by peer` - IB Gateway rejecting connection
- `Connection refused` - Port not accepting connections

This suggests IB Gateway might be:
1. Not fully connected to IB servers
2. Rejecting API connections despite settings
3. Settings not properly saved/applied

## Critical Checks

### 1. IB Gateway Connection Status
**Check IB Gateway window:**
- Is it showing "Connected" status? (not "Connecting" or "Disconnected")
- Are there any error messages visible?
- Can you see account information/positions?

**If not fully connected:**
- Wait for IB Gateway to fully connect
- Check internet connection
- Verify login credentials

### 2. Verify Settings Were Saved
**After making changes:**
1. Click **"Apply"** (if available)
2. Click **"OK"** (not Cancel)
3. **Close IB Gateway completely** (quit application)
4. **Reopen IB Gateway**
5. **Go back to Configure → API → Settings**
6. **Verify settings are still there:**
   - "Enable ActiveX and Socket Clients" still checked?
   - Port still 4002?
   - Trusted IPs still has 127.0.0.1?

### 3. Check API Logging
**In IB Gateway:**
- Go to: **Configure → API → Settings**
- Set **"Logging Level"** to **"Detail"** or **"Debug"**
- This will create API log files
- Check logs for connection attempts

**Log file locations:**
- `~/Documents/IB Gateway/` or `~/Documents/TWS/`
- Look for files named `api.log` or similar
- Check for connection attempts and errors

### 4. Try Different Port
**If port 4002 doesn't work:**
- Try port **4001** (IB Gateway live trading port)
- Or port **7497** (TWS paper trading port)
- Change in IB Gateway settings
- Restart IB Gateway
- Test with new port

### 5. macOS Firewall
**Check System Settings:**
- System Settings → Network → Firewall
- Make sure IB Gateway is allowed
- Or temporarily disable firewall to test

### 6. Contact IBKR Support
**If nothing works:**
- IBKR support can check account-specific settings
- They can verify API access is enabled on your account
- Some accounts need API access explicitly enabled

## Test Command
After each change:
```bash
source .venv/bin/activate
python scripts/check_ibkr_api.py
```

## Alternative: Use IBKR REST API
If socket API continues to fail, consider using IBKR's REST API instead:
- Different connection method
- May work when socket API doesn't
- Requires different implementation

