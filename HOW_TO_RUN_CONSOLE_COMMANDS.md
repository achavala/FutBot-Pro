# How to Run JavaScript Console Commands

## ⚠️ Important: Run in Browser Console, NOT Terminal

The JavaScript code must be run in your **browser's Developer Console**, not in the terminal (zsh).

## 📋 Step-by-Step Instructions

### Step 1: Open Browser Console
1. Open Chrome/Firefox/Safari
2. Navigate to: `http://localhost:8000/dashboard`
3. Press **F12** (or `Cmd+Option+I` on Mac, `Ctrl+Shift+I` on Windows)
4. Click the **"Console"** tab

### Step 2: Run the Diagnostic Code
Copy and paste this code into the **browser console** (not terminal):

```javascript
// Check if element exists now
const header = document.querySelector('.header-controls');
console.log('Header controls:', header);
console.log('Children:', header?.children);

// Check specific elements
console.log('simSymbol:', document.getElementById('simSymbol'));
console.log('simStartDate:', document.getElementById('simStartDate'));
console.log('replaySpeed:', document.getElementById('replaySpeed'));
```

### Step 3: Check Results
You should see output like:
```
Header controls: <div class="header-controls">...</div>
Children: HTMLCollection(6) [select#simSymbol, select#simStartDate, ...]
simSymbol: <select id="simSymbol">...</select>
simStartDate: <select id="simStartDate">...</select>
replaySpeed: <select id="replaySpeed">...</select>
```

## 🖼️ Visual Guide

1. **Browser Window** → Press F12
2. **DevTools Opens** → Click "Console" tab
3. **Paste Code** → In the console input area (bottom)
4. **Press Enter** → See results

## 🔍 Alternative: Use Elements Tab

1. Open DevTools (F12)
2. Click **"Elements"** tab
3. Press **Ctrl+F** (or `Cmd+F` on Mac)
4. Search for: `simStartDate`
5. If found → Element exists in HTML
6. If not found → Browser cache issue

## ✅ Quick Test

In browser console, run this one-liner:
```javascript
document.getElementById('simStartDate') ? '✅ Found!' : '❌ Not found'
```

If it says "❌ Not found", you need to:
1. **Hard refresh**: `Cmd+Shift+R` (Mac) or `Ctrl+Shift+R` (Windows)
2. **Or**: Open incognito/private window
3. **Or**: Clear browser cache

## 🚫 Don't Run in Terminal

The terminal (zsh) is for:
- Server commands
- Git commands
- Python scripts
- File operations

The browser console is for:
- JavaScript debugging
- DOM inspection
- Network monitoring
- Frontend testing


