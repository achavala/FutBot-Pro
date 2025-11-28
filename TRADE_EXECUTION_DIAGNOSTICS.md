# Trade Execution Diagnostics Guide

## Issues Fixed

### 1. ✅ Time Display Issue
**Problem**: Timestamp showing old time (e.g., 8 AM instead of 9:43 AM CST)

**Fix Applied**:
- Updated `last_bar_time` immediately when a bar is received in live mode
- Added debug logging to track bar processing
- Frontend now shows current CST time when bars are stuck (>5 min old)

**How to Verify**:
- Check the "Evaluating:" timestamp in the Status tab
- It should show current CST time when bot is running
- If bars are stuck, it will show "Live - Waiting for bars"

### 2. ✅ Diagnostic Logging Added
**Problem**: No visibility into why trades aren't executing

**Fix Applied**:
- Added comprehensive diagnostic logging in `_process_bar()`:
  - Regime type, confidence, bias
  - Intent validity, position delta, confidence
  - Trade execution reasons
  - Position delta calculations

**How to Check Logs**:
```bash
# View real-time diagnostic logs
tail -f logs/*.log | grep -E "TradeDiagnostic|TradeExecution"

# Or check server logs
tail -f /tmp/futbot_server.log | grep -E "TradeDiagnostic|TradeExecution"
```

### 3. ✅ TradingView Chart Integration
**Problem**: No visual chart analysis

**Fix Applied**:
- Added TradingView widget in Performance Analytics tab
- Auto-loads when Performance tab is opened
- Syncs with symbol selector (SPY/QQQ)
- Includes RSI, MACD, Volume indicators

**How to Use**:
1. Go to **Analytics** → **Performance** tab
2. Chart automatically loads for current symbol
3. Change symbol in header dropdown to update chart

## Why Trades Might Not Execute

Based on the diagnostic logging, check these conditions:

### 1. **Insufficient Bars** (Most Common)
- **Requirement**: Need 30+ bars for analysis
- **Check**: Look at "Bar #2563 | QQQ: 29, SPY: 29" in Status tab
- **Fix**: Wait for more bars or start a simulation to collect data

### 2. **Low Confidence**
- **Requirement**: Confidence ≥ 15% (lowered from 40%)
- **Check**: Look for `[TradeDiagnostic] Confidence: X.XX` in logs
- **Current**: If showing 0% confidence, regime engine needs more data

### 3. **Regime Not Suitable**
- **Requirement**: Regime should be TREND or EXPANSION (not COMPRESSION)
- **Check**: Status tab shows "compression | Bias: neutral"
- **Fix**: Wait for market regime to change, or lower confidence threshold further

### 4. **Position Delta = 0**
- **Check**: Logs show `position_delta: 0.0000`
- **Meaning**: Bot thinks current position is optimal
- **Fix**: This is normal if already in a good position

### 5. **Risk Manager Veto**
- **Check**: Logs show "Risk veto: [reason]"
- **Common reasons**:
  - Daily loss limit reached
  - Drawdown too high
  - Kill switch enabled
  - Position size too large

### 6. **Data Feed Not Getting Bars**
- **Check**: Bar count stuck at 29
- **Possible causes**:
  - Alpaca paper trading uses delayed data (15+ min old)
  - Market closed
  - API connection issues
- **Fix**: Check Alpaca connection, ensure market is open

## Diagnostic Commands

### Check Current Status
```bash
curl http://localhost:8000/live/status | jq
```

### Check Regime
```bash
curl http://localhost:8000/regime | jq
```

### Check Portfolio Stats
```bash
curl http://localhost:8000/stats | jq
```

### Monitor Trade Attempts
```bash
# Watch for trade execution attempts
tail -f logs/*.log | grep -E "TradeExecution|position_delta|Intent valid"
```

### Check Data Feed
```bash
# See if bars are being received
tail -f logs/*.log | grep -E "Processed bar|get_next_bar|bar for"
```

## Expected Log Output

### When Trade Should Execute:
```
🔍 [TradeDiagnostic] Symbol: SPY, Bar: 45
🔍 [TradeDiagnostic] Regime: TREND, Confidence: 0.75, Bias: BULLISH
🔍 [TradeDiagnostic] Intent valid: True, Position delta: 10.5000, Confidence: 0.72
🔍 [TradeDiagnostic] Reason: TrendAgent: Strong bullish trend signal
✅ [TradeExecution] Executing trade: SPY, Delta: 10.5000, Reason: ...
🚀 [TradeExecution] Executing trade: SPY, Delta: 10.5000, Price: $617.77, Reason: ...
✅ [TradeExecution] Trade executed successfully: SPY, 10.5 shares @ $617.77
```

### When Trade Won't Execute:
```
🔍 [TradeDiagnostic] Symbol: SPY, Bar: 29
🔍 [TradeDiagnostic] Regime: COMPRESSION, Confidence: 0.00, Bias: NEUTRAL
🔍 [TradeDiagnostic] Intent valid: False, Position delta: 0.0000, Confidence: 0.00
🔍 [TradeDiagnostic] Reason: Insufficient bars for analysis (need 30, have 29)
🔍 [TradeExecution] Intent invalid: Insufficient bars for analysis
```

## Next Steps

1. **Check the logs** - Run the diagnostic commands above
2. **Verify bar count** - Ensure you have 30+ bars
3. **Check regime** - Should be TREND or EXPANSION, not COMPRESSION
4. **Monitor confidence** - Should be ≥ 15%
5. **Check data feed** - Ensure bars are being received

## If Still No Trades

1. **Lower confidence threshold further** (in `config/settings.yaml`):
   ```yaml
   min_confidence: 0.10  # 10% instead of 15%
   ```

2. **Check if market is open** - Bot only trades during market hours

3. **Verify broker connection** - Ensure Alpaca credentials are correct

4. **Check kill switch** - Make sure it's not enabled

5. **Review risk limits** - Daily loss limits might be blocking trades

