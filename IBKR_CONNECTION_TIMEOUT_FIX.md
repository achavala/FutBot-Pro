# IBKR Connection Timeout Fix Guide

## Current Status
- ✅ API Settings: "Enable ActiveX and Socket Clients" is CHECKED
- ✅ Socket Port: 7497 (correct)
- ✅ Read-Only API: UNCHECKED
- ✅ API Precautions: All enabled
- ❌ Connection still timing out during API handshake

## Additional Settings to Check

### 1. Trusted IPs (CRITICAL)
In TWS, go to: **Configure → API → Settings**

Look for:
- **"Trusted IPs"** field or section
- **"Allow connections from localhost only"** checkbox

**Action**: 
- Add `127.0.0.1` to Trusted IPs
- OR check "Allow connections from localhost only" if available
- Click **OK** and **RESTART TWS**

### 2. Check API Logs
TWS creates API log files. Check:
- Look in TWS window for "API Logs" or "Logs" menu
- Or check: `~/Documents/IB Gateway/` or `~/Documents/TWS/` folders
- Look for connection attempts and error messages

### 3. Client ID Conflicts
Make sure no other application is using the same client ID:
- Close any other trading applications
- Try a different client ID (999, 888, 777, etc.)

### 4. TWS Version
Some TWS versions have known connection issues. Check your version:
- Help → About Trader Workstation
- If using an older version, try updating
- If using a very new version, there might be bugs

### 5. Firewall/Security
macOS firewall might be blocking:
- System Settings → Network → Firewall
- Check if TWS is allowed through firewall
- Or temporarily disable firewall to test

## Testing Steps

1. **Add Trusted IPs** (if not already done):
   - Configure → API → Settings
   - Add `127.0.0.1` to Trusted IPs
   - Click OK
   - **RESTART TWS**

2. **Test connection**:
   ```bash
   source .venv/bin/activate
   python scripts/check_ibkr_api.py
   ```

3. **If still failing, check TWS logs**:
   - Look for API connection attempts
   - Check for error messages

4. **Try different client ID**:
   ```bash
   curl -X POST http://localhost:8000/live/start \
     -H "Content-Type: application/json" \
     -d '{"symbols": ["QQQ"], "broker_type": "ibkr", "ibkr_host": "127.0.0.1", "ibkr_port": 7497, "ibkr_client_id": 999}'
   ```

## Common Issues

### Issue: "Connection timeout" but port is open
**Cause**: API socket server enabled but Trusted IPs not configured
**Fix**: Add `127.0.0.1` to Trusted IPs and restart

### Issue: "Connection reset by peer"
**Cause**: API Precautions blocking (already fixed)
**Fix**: Enable all API Precautions (already done)

### Issue: Works sometimes but not always
**Cause**: Client ID conflicts or TWS version issues
**Fix**: Use unique client IDs, update TWS

## Next Steps

1. Check if "Trusted IPs" section exists in API Settings
2. Add `127.0.0.1` if not already there
3. Restart TWS
4. Test connection again
5. Check TWS API logs for specific error messages

