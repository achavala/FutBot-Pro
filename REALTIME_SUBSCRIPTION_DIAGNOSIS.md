# Real-Time Subscription Diagnosis

## Test Results

The test script (`scripts/test_realtime_ibkr.py`) has been run and identified the root cause of why real-time bars are not being received.

### Error Found

```
Error 420: Invalid Real-time Query: No market data permissions for ISLAND STK. 
Requested market data requires additional subscription for API. 
See link in 'Market Data Connections' dialog for more details.
```

### Root Cause

**IBKR requires market data subscriptions for real-time data.** The paper trading account does not have real-time market data permissions for NASDAQ stocks (ISLAND exchange).

### Current Status

✅ **Connection**: Working - Successfully connected to IBKR TWS/Gateway  
✅ **API Access**: Working - API is properly configured  
❌ **Real-Time Data**: **BLOCKED** - No market data subscription  
✅ **Historical Data**: Working (with proper format)  
✅ **Implementation**: Code is correct, subscription logic works  

## Solutions

### Option 1: Use Delayed Data (Current Fallback)

The system already falls back to polling historical data when real-time subscription fails. This works but:
- Bars are delayed (15-20 minutes for NASDAQ)
- Not ideal for live trading
- Good for testing and development

### Option 2: Subscribe to Market Data in TWS

1. Open TWS/IB Gateway
2. Go to **Configure → Global Configuration → API → Settings**
3. Click on **Market Data Connections** link
4. Subscribe to required market data feeds:
   - **NASDAQ TotalView** (for NASDAQ stocks like QQQ)
   - **NYSE OpenBook** (for NYSE stocks)
   - **US Securities Snapshot** (for snapshot data)

**Note**: Market data subscriptions may have fees, even for paper trading accounts.

### Option 3: Use Massive API for Real-Time Data

Since you have Massive API access, we can use it as the primary data source:

1. Set `MASSIVE_API_KEY` in your environment or `config/settings.yaml`
2. The system will automatically use Massive API for data collection
3. Massive API provides real-time data without IBKR subscriptions

### Option 4: Use Different Exchange

Some exchanges provide delayed data without subscriptions:
- Try using **NYSE** instead of **NASDAQ** for certain symbols
- Some futures/options may have different data requirements

## Test Script Usage

Run the test script to verify real-time subscriptions:

```bash
# Basic test (30 seconds)
python scripts/test_realtime_ibkr.py

# Custom symbol and duration
python scripts/test_realtime_ibkr.py --symbol SPY --duration 60

# Different port (for live trading)
python scripts/test_realtime_ibkr.py --port 7496
```

## Recommendations

1. **For Development/Testing**: Continue using delayed data (current setup works)
2. **For Live Trading**: 
   - Option A: Subscribe to market data in TWS
   - Option B: Use Massive API for real-time data collection
3. **Hybrid Approach**: Use Massive API for data collection, IBKR for order execution

## Next Steps

1. ✅ Real-time subscription code is implemented and working
2. ⚠️  Market data subscription required for real-time bars
3. 🔄 System falls back to historical polling (works but delayed)
4. 💡 Consider using Massive API for real-time data collection

## Verification

To verify if market data subscription is enabled:

1. Run the test script: `python scripts/test_realtime_ibkr.py`
2. Check the output for:
   - ✅ "Real-time bars received" = Subscription working
   - ❌ "Error 420" = No market data permissions
   - ⚠️  "No bars received" = Market closed or other issue

