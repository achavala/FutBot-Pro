# IB Gateway 10.37.1m macOS ARM API Bug - Fix

## The Problem

IB Gateway 10.37.1m has a **known bug** on macOS ARM (Apple Silicon):
- Port opens ✅
- Socket connects ✅  
- API handshake never starts ❌
- Connection times out ❌

This is **not your code** - it's an IBKR bug.

## Quick Fixes (Choose One)

### Option 1: Run IB Gateway in Rosetta Mode (Easiest)

1. **Quit IB Gateway** completely
2. **Right-click** IB Gateway app → **Get Info**
3. Check **"Open using Rosetta"**
4. **Restart IB Gateway**
5. Test connection again

This often fixes the API activation issue.

### Option 2: Use TWS Instead

TWS (Trader Workstation) works reliably on macOS ARM:

1. Download TWS: https://www.interactivebrokers.com/en/index.php?f=16042
2. Install and launch TWS
3. Configure API: **Configure → API → Settings**
   - Check "Enable ActiveX and Socket Clients"
   - Set port to **7497** (paper) or **7496** (live)
4. Use port **7497** or **7496** in FutBot instead of 4002

### Option 3: Downgrade to IB Gateway 10.19

Stable version that works on macOS ARM:

1. Download Gateway 10.19: https://www.interactivebrokers.com/en/index.php?f=16457
2. Uninstall current Gateway (optional)
3. Install 10.19
4. Configure API settings
5. Test connection

## Testing After Fix

```bash
python scripts/diagnose_ibkr.py
```

Should show: `✅ Successfully connected!`

## Using with FutBot

Once connection works, use the appropriate port:

**For TWS:**
```bash
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

**For Gateway 10.19 (after Rosetta fix):**
```bash
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["QQQ"],
    "broker_type": "ibkr",
    "ibkr_host": "127.0.0.1",
    "ibkr_port": 4002,
    "ibkr_client_id": 1
  }'
```

