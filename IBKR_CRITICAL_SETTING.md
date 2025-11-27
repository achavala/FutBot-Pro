# Critical IBKR API Setting

## The Missing Setting

Based on your screenshots, I can see:
- ✅ Socket port is set to 4002
- ✅ Trusted IPs includes 127.0.0.1
- ✅ Allow connections from localhost only is checked

**However, there's one critical setting that must be enabled:**

## "Enable ActiveX and Socket Clients"

This setting is usually on the **main API Settings page** (the first tab you showed).

### Where to Find It:

1. In IB Gateway, go to: **Configure** → **API** → **Settings**
2. Look for a checkbox at the **top** of the settings list that says:
   - **"Enable ActiveX and Socket Clients"**
   - OR
   - **"Enable Socket Clients"**
   - OR
   - **"Enable API"**

3. This checkbox **MUST be checked** ✅

### If You Don't See It:

Sometimes this setting is:
- On a different tab (check all tabs in the API Settings window)
- At the very top of the list (scroll up)
- In a separate "Connection" or "Security" section

### After Enabling:

1. Click **OK** to save
2. **Restart IB Gateway completely** (close and reopen)
3. Test connection:
   ```bash
   python scripts/diagnose_ibkr.py
   ```

## What Your Settings Should Look Like:

```
✅ Enable ActiveX and Socket Clients  ← THIS MUST BE CHECKED
✅ Socket port: 4002
✅ Allow connections from localhost only
✅ Trusted IPs: 127.0.0.1
```

## Still Can't Find It?

If you can't find this setting:
1. Check if you're using IB Gateway or TWS (TWS has more settings)
2. Look in **Configure** → **API** → **Precautions** (sometimes it's there)
3. Try updating IB Gateway to the latest version
4. The setting might be named slightly differently in your version

## Quick Test After Enabling:

```bash
python scripts/diagnose_ibkr.py
```

You should see:
```
✅ Successfully connected on port 4002!
💡 Use port 4002 in your connection settings
```

