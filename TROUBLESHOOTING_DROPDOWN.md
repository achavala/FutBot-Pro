# Troubleshooting Date Dropdown Issue

## Issue
User reports:
- Date dropdown not visible
- Nothing happens when clicking Simulate button

## Possible Causes

### 1. Browser Cache
**Solution**: Hard refresh the page
- **Chrome/Edge**: `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac)
- **Firefox**: `Ctrl+F5` (Windows) or `Cmd+Shift+R` (Mac)
- **Safari**: `Cmd+Option+R`

### 2. JavaScript Not Running
**Check**: Open browser console (F12) and look for:
- Errors in red
- Console log: "Populating date dropdown..."
- Console log: "Date dropdown populated with X dates"

**If no logs appear**: JavaScript might be blocked or not loading

### 3. Element Not Found
**Check**: In browser console, run:
```javascript
document.getElementById('simStartDate')
document.getElementById('simSymbol')
```

**Expected**: Should return the `<select>` elements, not `null`

### 4. CSS Hiding Elements
**Check**: In browser console, run:
```javascript
const dateSelect = document.getElementById('simStartDate');
console.log('Display:', window.getComputedStyle(dateSelect).display);
console.log('Visibility:', window.getComputedStyle(dateSelect).visibility);
```

**Expected**: `display: inline-block`, `visibility: visible`

## Quick Fix Steps

1. **Hard refresh the page** (most common fix)
2. **Check browser console** for errors
3. **Verify server is running** latest code:
   ```bash
   curl http://localhost:8000/dashboard | grep -i "simStartDate"
   ```
   Should show: `<select id="simStartDate"`

4. **Clear browser cache**:
   - Chrome: Settings → Privacy → Clear browsing data → Cached images and files
   - Firefox: Settings → Privacy → Clear Data → Cached Web Content

5. **Try incognito/private window** to bypass cache

## Expected UI Elements

After refresh, you should see in the header:
1. **Symbol dropdown** (SPY/QQQ) - 100px wide
2. **Date dropdown** (with dates) - 180px wide  
3. **Replay speed dropdown** (1x, 10x, 50x, 100x, 600x) - 120px wide
4. **Simulate button** (blue)

## Debugging Commands

### Check if dropdown is populated:
```javascript
const select = document.getElementById('simStartDate');
console.log('Options count:', select.options.length);
console.log('Options:', Array.from(select.options).map(o => o.textContent));
```

### Manually trigger population:
```javascript
populateDateDropdown();
```

### Check if Simulate button works:
```javascript
startSimulation();
```

## Server Restart

If changes aren't showing:
```bash
# Kill existing server
kill -9 $(lsof -ti:8000) 2>/dev/null

# Restart
cd /Users/chavala/FutBot
source .venv/bin/activate
python main.py --mode api --port 8000
```

## Verification

After refresh, the date dropdown should:
- Show "All Available Data" as first option
- Show ~60-65 weekdays from last 3 months
- Format: "Mon, Nov 25, 2024"
- Most recent dates at top

If still not working, check:
1. Browser console for JavaScript errors
2. Network tab for failed resource loads
3. Server logs: `tail -f /tmp/futbot_server.log`


