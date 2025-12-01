# Automatic Trading Setup - SPY/QQQ

## ✅ Changes Implemented

### 1. **Profit Target: 15% | Stop Loss: 10%**
- Updated `config/settings.yaml` for SPY and QQQ
- Updated `core/live/profit_manager.py` default values
- **Take Profit**: 15% gain triggers automatic sell
- **Stop Loss**: 10% loss triggers automatic sell

### 2. **Automatic Trading During Market Hours**
- **No manual selection needed** - bot auto-starts during trading hours
- **Auto-starts with SPY and QQQ** when market opens (9:30 AM - 4:00 PM ET)
- **Simulation controls hidden** during trading hours
- **No market status display** - clean interface

### 3. **Lowered Confidence Thresholds**
- **Minimum confidence**: Lowered from 0.25 to 0.15
- **Very lenient thresholds**: 0.1 for low confidence signals
- **Ensures trades execute** - system will trade more actively

### 4. **Trading Logic**
- Bot uses its intelligence algorithm to:
  - Analyze market conditions (regime, trend, volatility)
  - Evaluate agent signals (trend, mean reversion, volatility, FVG)
  - Make buy/sell decisions automatically
  - Execute trades when conditions are favorable

## 🚀 How It Works

### During Market Hours (9:30 AM - 4:00 PM ET):

1. **Auto-Start**: Bot automatically starts trading with SPY and QQQ
2. **No Controls Visible**: Simulation controls are hidden
3. **Automatic Trading**: Bot makes buy/sell decisions using its algorithm
4. **Profit Management**:
   - **Buy** when algorithm detects good setup (15%+ profit potential)
   - **Sell** at 15% profit OR 10% stop loss

### After Market Hours:

1. **Simulation Controls Appear**: You can run historical simulations
2. **Trading Stops**: Live trading automatically stops

## 📊 Trading Rules

### Entry Conditions (Automatic Buy):
- Regime confidence ≥ 15% (lowered threshold)
- Agent signals indicate favorable conditions
- Risk manager allows trading
- Algorithm detects 15%+ profit potential

### Exit Conditions (Automatic Sell):
- **Take Profit**: Position reaches 15% gain
- **Stop Loss**: Position reaches 10% loss
- **Regime Change**: Market conditions become unfavorable
- **Bias Flip**: Market direction changes

## 🔧 Configuration Files

### `config/settings.yaml`:
```yaml
SPY:
  take_profit_pct: 0.15  # 15% profit target
  stop_loss_pct: 0.10    # 10% stop loss

QQQ:
  take_profit_pct: 0.15  # 15% profit target
  stop_loss_pct: 0.10    # 10% stop loss
```

### `core/policy/controller.py`:
- Minimum confidence: 0.15 (lowered from 0.25)
- Very lenient thresholds to ensure trades execute

## 📈 What You'll See

### During Trading Hours:
- ✅ **Simulation controls hidden** (no options to select)
- ✅ **Bot auto-starts** with SPY and QQQ
- ✅ **Trades appear automatically** in "Positions & Recent Trades"
- ✅ **Status tab shows** trade setups and agent activity

### Trade Execution:
- Bot will **automatically buy** when it detects good setups
- Bot will **automatically sell** at:
  - 15% profit (take profit)
  - 10% loss (stop loss)
  - Regime change or bias flip

## ⚠️ Important Notes

1. **Paper Trading**: Currently set to `broker_type: "paper"` for safety
2. **Auto-Start Delay**: Waits 3 seconds after page load before auto-starting
3. **Confidence Thresholds**: Lowered to ensure trades execute
4. **Market Hours**: 9:30 AM - 4:00 PM ET, weekdays only

## 🎯 Expected Behavior

### Today During Trading Hours:
1. **Page loads** → Bot detects market is open
2. **3 seconds later** → Auto-starts trading with SPY and QQQ
3. **After 30+ bars** → Bot starts analyzing and making decisions
4. **When good setup detected** → Bot automatically buys
5. **When profit/loss targets hit** → Bot automatically sells

### You Should See:
- ✅ Trades appearing in "Positions & Recent Trades" table
- ✅ Status tab showing "GOOD SETUP" when conditions are favorable
- ✅ Automatic buy/sell orders executing
- ✅ Profit/loss tracking in real-time

## 🔍 Troubleshooting

### If No Trades Appear:

1. **Check if bot is running**:
   - Look for "System Running" in header
   - Check Status tab for "Live - Running"

2. **Check bar count**:
   - Need at least 30 bars for analysis
   - Status tab shows progress (X/30 bars)

3. **Check confidence**:
   - Status tab shows regime confidence
   - If confidence is very low, bot may wait for better setup

4. **Check risk manager**:
   - Risk manager may block trades if limits are hit
   - Check Risk Mgmt tab for status

5. **Check broker connection**:
   - Ensure broker (Alpaca/IBKR) is connected
   - Check logs for connection errors

---

**Status**: ✅ Automatic trading enabled
**Profit Target**: 15%
**Stop Loss**: 10%
**Symbols**: SPY, QQQ
**Mode**: Paper Trading (safe testing)


