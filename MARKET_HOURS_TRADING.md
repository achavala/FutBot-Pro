# Market Hours Trading Guide

## ✅ Features Implemented

### 1. **Market Hours Detection**
- Automatically detects if US market is open (9:30 AM - 4:00 PM ET, weekdays only)
- Handles DST (Daylight Saving Time) correctly
- Updates every minute

### 2. **Simulation Disabled During Trading Hours**
- **Simulation button is automatically disabled** when market is open
- All simulation controls (symbol selector, date/time inputs, replay speed) are disabled
- Clear error message if user tries to simulate during trading hours
- **"Start Live" button remains enabled** for live trading

### 3. **Market Status Display**
- Shows market status in the header: "Market OPEN" or "Market CLOSED"
- Displays current Eastern Time
- Updates in real-time

## 🚀 How to Test SPY/QQQ During Trading Hours

### Step 1: Check Market Status
The dashboard automatically shows:
- **"Market OPEN"** in the header when trading hours are active
- Current Eastern Time
- Simulation button is grayed out and disabled

### Step 2: Start Live Trading
1. Click **"Start Live"** button (green play icon)
2. Select your symbols (SPY or QQQ)
3. The bot will:
   - Connect to your broker (Alpaca/IBKR)
   - Start collecting real-time bars
   - Analyze market conditions
   - Show trade setups in the **Status** tab

### Step 3: Check for Good Setups
Navigate to **Analytics → Performance → Status** tab to see:

#### Trade Setups Card
- **GOOD SETUP** (Green) - Strong trading signal, high confidence
- **CAUTION** (Orange) - Moderate confidence, wait for better setup
- **AVOID** (Red) - Poor conditions, low confidence

#### What Makes a Good Setup?
A **GOOD SETUP** appears when:
- ✅ **Confidence ≥ 70%**
- ✅ **Bias is BULLISH or BEARISH** (not NEUTRAL)
- ✅ **Regime is TREND or EXPANSION** (not COMPRESSION)
- ✅ **At least 30 bars collected** for reliable analysis

#### Current Evaluation Info
- **Evaluating Bar**: Shows the exact timestamp being analyzed
- **Bar Count**: Shows how many bars have been processed
- **Regime Details**: Shows regime type, bias, and confidence level

### Step 4: Monitor Agent Activity
The **Agent Activity** section shows:
- Which agents are active
- Agent fitness scores
- Agent weights (how much each agent influences decisions)

### Step 5: Watch for Trades
- **Positions & Recent Trades** table will show executed trades
- Trades appear when:
  - Good setup is detected
  - Risk manager allows trading
  - Controller confidence is high enough
  - Position delta is non-zero

## 📊 Example: Checking SPY Setup Right Now

1. **Open Dashboard**: `http://localhost:8000/dashboard`
2. **Check Header**: Should show "Market OPEN" if it's 9:30 AM - 4:00 PM ET on a weekday
3. **Click "Start Live"**: Select SPY as symbol
4. **Wait for 30+ bars**: Status tab will show progress (X/30 bars)
5. **Check Trade Setups**:
   - If you see **"GOOD SETUP"** → Conditions are favorable
   - If you see **"CAUTION"** → Wait for better conditions
   - If you see **"AVOID"** → Market is choppy, avoid trading

## 🔧 API Endpoints

### Check Market Status
```bash
curl http://localhost:8000/market/status
```

Response:
```json
{
  "is_open": true,
  "current_time_et": "2024-11-27 14:30:00 ET",
  "current_time_utc": "2024-11-27 19:30:00 UTC",
  "is_weekday": true,
  "trading_hours": "9:30 AM - 4:00 PM ET"
}
```

### Check Current Regime
```bash
curl http://localhost:8000/regime
```

### Check Live Status
```bash
curl http://localhost:8000/live/status
```

## ⚠️ Important Notes

1. **Simulation is disabled during trading hours** to prevent confusion
2. **Live trading requires broker connection** (Alpaca or IBKR)
3. **Minimum 30 bars needed** for reliable analysis
4. **Market hours**: 9:30 AM - 4:00 PM ET, Monday-Friday only
5. **After hours**: Simulation is re-enabled automatically when market closes

## 🎯 Quick Test Checklist

- [ ] Market is open (9:30 AM - 4:00 PM ET, weekday)
- [ ] Simulation button is disabled/grayed out
- [ ] "Start Live" button is enabled
- [ ] Click "Start Live" with SPY or QQQ
- [ ] Wait for 30+ bars to collect
- [ ] Check Status tab for trade setup
- [ ] Monitor for "GOOD SETUP" signal
- [ ] Watch for trades in "Positions & Recent Trades"

## 📈 Understanding Trade Setups

### GOOD SETUP (Green)
- **When**: High confidence (≥70%), strong trend, clear bias
- **Action**: Favorable conditions for trading
- **Example**: "Strong bullish signal in trend regime"

### CAUTION (Orange)
- **When**: Moderate confidence (40-70%), mixed signals
- **Action**: Wait for better setup, or trade with smaller size
- **Example**: "Moderate confidence (55%) - wait for better setup"

### AVOID (Red)
- **When**: Low confidence (<40%), choppy market, compression regime
- **Action**: Do not trade, wait for better conditions
- **Example**: "Low confidence (0%) or choppy market"

---

**Status**: ✅ Market hours detection active
**Simulation**: Disabled during trading hours (9:30 AM - 4:00 PM ET)
**Live Trading**: Enabled and ready

