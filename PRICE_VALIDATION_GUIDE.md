# Price Validation Guide

## 🎯 Purpose

This guide provides step-by-step instructions to validate that trade prices match real market data (e.g., Webull) after the price mismatch fixes.

---

## ✅ Step 1: Re-run QQQ Simulation

Use the same offline config you used before:

```bash
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["QQQ"],
    "broker_type": "cached",
    "offline_mode": true,
    "testing_mode": true,
    "replay_speed": 600.0,
    "start_time": "2025-11-26T09:30:00",
    "end_time": "2025-11-26T10:00:00",
    "fixed_investment_amount": 10000.0
  }'
```

Wait for simulation to complete (should finish in < 5 seconds).

---

## ✅ Step 2: Get Round-Trip Trades

Fetch the round-trip trades:

```bash
curl -s "http://localhost:8000/trades/roundtrips?symbol=QQQ&limit=5" \
  | python3 -m json.tool
```

**Expected Structure:**
```json
{
  "trades": [
    {
      "symbol": "QQQ",
      "direction": "LONG",
      "entry_time": "2025-11-26T14:35:00+00:00",
      "exit_time": "2025-11-26T15:05:00+00:00",
      "entry_price": 611.20,
      "exit_price": 613.80,
      "quantity": 16.35,
      "gross_pnl": 42.51,
      "pnl_pct": 0.42,
      "duration_minutes": 30.0,
      "reason": "Trend follow on strong EMA / ADX",
      "agent": "trend_agent",
      "regime_at_entry": "TREND",
      "vol_bucket_at_entry": "MEDIUM"
    }
  ],
  "total_count": 1
}
```

**Key Fields to Note:**
- `entry_time` - When the trade was entered
- `entry_price` - Price at entry (should match Webull)
- `exit_time` - When the trade was closed
- `exit_price` - Price at exit
- `regime_at_entry` - Market regime when entered
- `vol_bucket_at_entry` - Volatility level when entered

---

## ✅ Step 3: Verify Cached Data Was Used

Check logs to confirm cached data was used (not synthetic):

```bash
grep -E "SyntheticBarFallback|cached data|Loading data from" /tmp/futbot_server.log | tail -20
```

**✅ Good Signs:**
- `Loading cached data for QQQ...`
- `Loading data from 2025-11-26 to 2025-11-26 for QQQ`
- **NO** `[SyntheticBarFallback]` entries

**❌ Bad Signs:**
- `[SyntheticBarFallback] No cached data found`
- `Generated SYNTHETIC bars`
- `⚠️ These are SYNTHETIC bars`

If you see synthetic bars, check:
1. Date range in cache vs requested range
2. Timezone alignment (should be UTC)
3. Symbol name matching (QQQ vs qqq)

---

## ✅ Step 4: Cross-Check with Webull

### 4.1 Convert Entry Time to Local Timezone

Take the `entry_time` from the trade (e.g., `2025-11-26T14:35:00+00:00`).

Convert to EST (US market hours):
- UTC: `14:35` = `2:35 PM UTC`
- EST: `14:35 UTC` = `9:35 AM EST` (UTC-5)

### 4.2 Check Webull Chart

1. Open Webull
2. Navigate to QQQ 5-minute chart
3. Go to Nov 26, 2025
4. Find the candle at `9:35 AM EST` (or your entry_time converted)
5. Check the **close price** of that candle

### 4.3 Compare Prices

**Expected Match:**
- Webull close price: `~611.20`
- Your `entry_price`: `~611.20`
- **Difference should be < $0.50** (slippage/timing)

**If Mismatch:**
- If Webull ≈ 611 but your price ≈ 488:
  - ❌ Still using synthetic bars OR
  - ❌ Cached data is wrong (upstream issue)
- If Webull ≈ 611 and your price ≈ 611:
  - ✅ **Price integrity is correct!**

---

## ✅ Step 5: Validate Multiple Trades

Repeat Step 4 for 3-5 different trades to ensure consistency:

```bash
# Get all QQQ trades
curl -s "http://localhost:8000/trades/roundtrips?symbol=QQQ" | python3 -m json.tool

# For each trade:
# 1. Note entry_time and entry_price
# 2. Check Webull at that time
# 3. Verify prices match
```

---

## 🔍 Troubleshooting

### Issue: Still seeing ~488 prices

**Possible Causes:**
1. **Synthetic bars still being used**
   - Check logs for `[SyntheticBarFallback]`
   - Verify date range matches cached data
   - Check timezone alignment

2. **Cached data is wrong**
   - Verify data collection: `python3 scripts/collect_historical_data.py --stocks QQQ --start-date 2025-11-26 --end-date 2025-11-27`
   - Check cache: `sqlite3 data/cache.db "SELECT ts, close FROM polygon_bars WHERE symbol='QQQ' AND ts >= 1732608000000 LIMIT 10;"`

3. **Date mismatch**
   - Verify simulation is using correct date
   - Check timezone conversion (UTC vs EST)

### Issue: No trades generated

**Possible Causes:**
1. Agents not generating intents
   - Check logs for `[Controller]` messages
   - Verify agents are evaluating correctly

2. Risk manager blocking trades
   - Check `testing_mode: true` is set
   - Review risk manager logs

---

## 📊 Success Criteria

**Price Integrity is VALIDATED if:**
- ✅ All trades show prices in 600-650 range (for QQQ in Nov 2025)
- ✅ Entry prices match Webull within $0.50
- ✅ No `[SyntheticBarFallback]` in logs
- ✅ Cached data is being used

**Round-Trip Trades are VALIDATED if:**
- ✅ All trades have `entry_time` < `exit_time`
- ✅ `regime_at_entry` and `vol_bucket_at_entry` are populated
- ✅ P&L calculations are correct
- ✅ Duration is reasonable

---

## 🎯 Next Steps After Validation

Once prices are validated:
1. ✅ Lock price integrity as "verified"
2. ✅ Use round-trip trades for P&L analysis
3. ✅ Build regime/volatility heatmaps
4. ✅ Proceed to Phase 2 (ML enhancements)

---

**Status:** Ready for validation ✅


