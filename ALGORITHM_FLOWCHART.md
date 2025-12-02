# FutBot Trading Algorithm - Call Flow Diagram

## Overview
This document shows the complete call flow of the trading algorithm, from user action to trade execution.

---

## 1. SYSTEM STARTUP FLOW

```
[User Action]
    │
    ├─> Dashboard: Click "Start Live" / "Simulate"
    │   OR
    └─> API: POST /start-live
            │
            ▼
[ui/fastapi_app.py]
    start_live_trading()
            │
            ├─> Initialize broker_client (Alpaca/Paper/IBKR)
            ├─> Initialize data_feed (Cached/Alpaca/IBKR)
            ├─> Load asset_profiles from config
            ├─> Create LiveTradingConfig
            │   └─> fixed_investment_amount: $1000 (default)
            │   └─> symbols: ["SPY", "QQQ"]
            │   └─> testing_mode: True/False
            │
            ▼
[ui/bot_manager.py]
    BotManager.start_live_trading()
            │
            ├─> Create LiveTradingLoop(config)
            │   └─> core/live/scheduler.py
            │
            └─> Start background thread
                └─> loop.run()
```

---

## 2. MAIN TRADING LOOP FLOW

```
[core/live/scheduler.py]
LiveTradingLoop.run()
    │
    ├─> Initialize components:
    │   ├─> PortfolioManager
    │   ├─> RiskManager / AdvancedRiskManager
    │   ├─> LiveTradeExecutor
    │   ├─> OptionsExecutor (if options enabled)
    │   ├─> MultiLegProfitManager
    │   ├─> DeltaHedgeManager (if delta hedging enabled)
    │   └─> Agents (DirectionalAgent, ThetaHarvesterAgent, GammaScalperAgent)
    │
    ├─> Load historical bars (if offline_mode)
    │   └─> data_feed.get_bars(symbol, start_date, end_date)
    │
    └─> MAIN LOOP:
        │
        ├─> Get next bar(s) from data_feed
        │   └─> data_feed.get_next_bar(symbol) OR get_batch_bars()
        │
        ├─> For each symbol:
        │   │
        │   └─> _process_bar(symbol, bar)
        │       │
        │       ├─> [STEP 1] Validate bar
        │       │   └─> Check bar.symbol == symbol (prevent price mismatch)
        │       │
        │       ├─> [STEP 2] Update portfolio with current price
        │       │   └─> portfolio.update_position(symbol, bar.close)
        │       │
        │       ├─> [STEP 3] Compute features & regime
        │       │   ├─> feature_engine.compute_features(bars)
        │       │   ├─> regime_engine.classify_regime(features)
        │       │   └─> Returns: RegimeSignal
        │       │       └─> regime_type: TREND/COMPRESSION/EXPANSION/etc
        │       │       └─> bias: BULLISH/BEARISH/NEUTRAL
        │       │       └─> confidence: 0.0-1.0
        │       │
        │       ├─> [STEP 4] Check profit-taking (existing positions)
        │       │   └─> profit_manager.should_take_profit()
        │       │       └─> If True: Close position
        │       │
        │       ├─> [STEP 5] Get trade decision from agents
        │       │   └─> meta_policy.decide(signal, market_state, agents)
        │       │       ├─> For each agent:
        │       │       │   └─> agent.decide(signal, market_state)
        │       │       │       └─> Returns: TradeIntent
        │       │       └─> Combine intents → FinalTradeIntent
        │       │           └─> position_delta: float (signal strength)
        │       │           └─> confidence: float
        │       │           └─> primary_agent: str
        │       │
        │       ├─> [STEP 6] Check if options trade
        │       │   └─> If intent.is_options_trade:
        │       │       └─> [OPTIONS PATH] (see section 3)
        │       │
        │       └─> [STEP 7] Stock trade execution
        │           └─> [STOCK PATH] (see section 4)
        │
        └─> Sleep until next bar (based on replay_speed_multiplier)
```

---

## 3. OPTIONS TRADE EXECUTION FLOW

```
[core/live/scheduler.py]
_process_bar() → Options Path
    │
    ├─> Check if options trade
    │   └─> intent.is_options_trade == True
    │       └─> intent.option_symbol != None
    │
    ├─> [OPTIONS EXECUTION]
    │   └─> options_executor.execute_intent(intent, symbol, bar.close)
    │       │
    │       ├─> [core/live/executor_options.py]
    │       │   SyntheticOptionsExecutor.execute_intent()
    │       │
    │       ├─> Check if multi-leg trade (straddle/strangle)
    │       │   └─> If intent.strategy == "theta_harvester" OR "gamma_scalper"
    │       │       └─> _execute_multi_leg_trade()
    │       │           │
    │       │           ├─> Submit CALL order
    │       │           │   └─> broker_client.place_order()
    │       │           │
    │       │           ├─> Submit PUT order
    │       │           │   └─> broker_client.place_order()
    │       │           │
    │       │           ├─> Track fills separately
    │       │           │   └─> options_portfolio.add_multi_leg_position()
    │       │           │
    │       │           └─> Verify credit/debit matches expected
    │       │
    │       └─> Single-leg options trade
    │           └─> broker_client.place_order()
    │
    ├─> [MULTI-LEG PROFIT TRACKING]
    │   └─> multi_leg_profit_manager.track_position()
    │       └─> core/live/multi_leg_profit_manager.py
    │
    ├─> [DELTA HEDGING CHECK] (if Gamma Scalper)
    │   └─> delta_hedge_manager.check_and_hedge()
    │       └─> core/live/delta_hedge_manager.py
    │           │
    │           ├─> Calculate net_delta from options position
    │           ├─> If |net_delta| > threshold (0.10):
    │           │   └─> Calculate hedge_shares = -net_delta * 100
    │           │   └─> Execute hedge trade (buy/sell underlying)
    │           │
    │           └─> Track hedge P&L separately
    │
    └─> [MULTI-LEG EXIT CHECK]
        └─> _check_multi_leg_exits()
            └─> multi_leg_profit_manager.should_close_multi_leg_position()
                │
                ├─> Check TP/SL rules
                ├─> Check IV collapse (Theta Harvester)
                ├─> Check GEX reversal (Gamma Scalper)
                └─> If exit: Close both legs + flatten hedge
```

---

## 4. STOCK TRADE EXECUTION FLOW (WHERE BUG WAS FIXED)

```
[core/live/scheduler.py]
_process_bar() → Stock Path
    │
    ├─> [POSITION SIZING CALCULATION] ⚠️ BUG FIXED HERE
    │   │
    │   ├─> Get base_investment_amount
    │   │   ├─> From asset_profile.fixed_investment_amount
    │   │   └─> OR config.fixed_investment_amount (default: $1000)
    │   │
    │   ├─> Calculate target_quantity
    │   │   └─> target_quantity = base_investment / bar.close
    │   │       └─> Example: $1000 / $670 = 1.49 shares
    │   │
    │   ├─> Apply direction (buy/sell)
    │   │   └─> If intent.position_delta > 0: buy
    │   │   └─> If intent.position_delta < 0: sell
    │   │
    │   ├─> Calculate position_delta needed
    │   │   └─> position_delta = target_quantity - current_position
    │   │
    │   └─> [RISK MANAGEMENT] ⚠️ BUG WAS HERE
    │       │
    │       ├─> If advanced_risk enabled:
    │       │   │
    │       │   ├─> If testing_mode:
    │       │   │   └─> adjusted_size = base_investment * confidence_factor
    │       │   │
    │       │   └─> Else (production):
    │       │       └─> advanced_risk.compute_advanced_position_size()
    │       │           │
    │       │           ├─> [core/risk/advanced.py]
    │       │           │   compute_advanced_position_size()
    │       │           │
    │       │           ├─> Start with: size = base_investment ($1000)
    │       │           │
    │       │           ├─> Check hard stops (drawdown, circuit breaker)
    │       │           │   └─> If triggered: return 0.0
    │       │           │
    │       │           ├─> Apply regime-aware cap ⚠️ BUG FIXED
    │       │           │   └─> BEFORE: max_size = (capital * pct) / price ❌
    │       │           │   └─> AFTER:  max_size = capital * pct ✅
    │       │           │       └─> Example: $100k * 5% = $5000 max
    │       │           │
    │       │           ├─> Apply volatility scaling
    │       │           │   └─> Reduce size if high volatility
    │       │           │
    │       │           ├─> Apply confidence scaling
    │       │           │   └─> size = size * confidence
    │       │           │       └─> Example: $1000 * 0.3 = $300
    │       │           │
    │       │           ├─> Check VaR limit
    │       │           │   └─> Cap size if VaR too high
    │       │           │
    │       │           └─> Apply symbol exposure cap ⚠️ BUG FIXED
    │       │               └─> BEFORE: max_exposure = (capital * pct) / price ❌
    │       │               └─> AFTER:  max_exposure = capital * pct ✅
    │       │
    │       └─> Convert dollar size to quantity
    │           └─> max_quantity = adjusted_size / bar.close
    │
    ├─> [CAP POSITION DELTA]
    │   └─> If |position_delta| > |max_quantity|:
    │       └─> position_delta = max_quantity (capped)
    │
    ├─> [EXECUTE TRADE]
    │   └─> executor.apply_intent(modified_intent, symbol, bar.close, current_position)
    │       │
    │       ├─> [core/live/executor_live.py]
    │       │   LiveTradeExecutor.apply_intent()
    │       │
    │       ├─> Calculate target_position
    │       │   └─> target_position = current_position + position_delta
    │       │
    │       ├─> Determine order side & quantity
    │       │   ├─> If target > current: BUY
    │       │   └─> If target < current: SELL
    │       │
    │       ├─> Apply risk constraints
    │       │   └─> Cap quantity if exceeds max_size
    │       │
    │       └─> Submit order to broker
    │           └─> broker_client.place_order()
    │               │
    │               ├─> [core/live/broker_client.py]
    │               │   PaperBrokerClient.place_order()
    │               │   │
    │               │   ├─> Create Order object
    │               │   ├─> Simulate fill (or real fill if Alpaca)
    │               │   └─> Return Order with filled_quantity
    │               │
    │               └─> [core/live/broker_client_ibkr.py] (if IBKR)
    │                   └─> Real order via IB API
    │
    └─> [UPDATE PORTFOLIO]
        └─> portfolio.apply_position_delta(quantity, fill_price, timestamp)
            │
            ├─> [core/portfolio/manager.py]
            │   PortfolioManager.apply_position_delta()
            │
            ├─> Update position quantity
            ├─> Update average entry price
            ├─> Calculate unrealized P&L
            └─> Record trade in history
```

---

## 5. KEY TROUBLESHOOTING POINTS

### 🔴 Critical Checkpoints (Where Bugs Often Occur)

#### A. Price Mismatch Prevention
```
Location: core/live/scheduler.py:_process_bar()
Line: ~596, ~1164
Check: bar.symbol == symbol
Issue: Wrong price used for wrong symbol
Fix: Skip bar if mismatch detected
```

#### B. Position Sizing Calculation ⚠️ RECENTLY FIXED
```
Location: core/risk/advanced.py:compute_advanced_position_size()
Line: 237, 256
Issue: Dividing by price when calculating caps (unit mismatch)
Fix: Removed division by price - caps now in dollars
```

#### C. Quantity Calculation
```
Location: core/live/scheduler.py:_process_bar()
Line: 1101, 1136
Check: target_quantity = base_investment / bar.close
Issue: Wrong price → wrong quantity
Fix: Use bar.close (not latest["close"])
```

#### D. Multi-Leg Fill Tracking
```
Location: core/live/executor_options.py:_execute_multi_leg_trade()
Line: ~800-850
Issue: Legs filled separately, need to track both
Check: Both call_fill and put_fill exist
```

#### E. Delta Hedging Calculation
```
Location: core/live/delta_hedge_manager.py:calculate_hedge_quantity()
Line: ~200-250
Issue: Net delta calculation, hedge sizing
Check: hedge_shares = -net_delta * 100 (correct units)
```

---

## 6. DATA FLOW SUMMARY

```
User Action
    │
    ▼
[API/Dashboard]
    │
    ▼
[BotManager]
    │
    ▼
[LiveTradingLoop]
    │
    ├─> Data Feed → Bars
    ├─> Feature Engine → Features
    ├─> Regime Engine → RegimeSignal
    ├─> Agents → TradeIntent
    ├─> Meta Policy → FinalTradeIntent
    ├─> Risk Manager → Position Size
    ├─> Executor → Order
    ├─> Broker Client → Fill
    └─> Portfolio Manager → Position Update
```

---

## 7. COMMON ISSUES & WHERE TO CHECK

| Issue | Location | File | Line Range |
|-------|----------|------|------------|
| **Tiny position sizes** | Position sizing | `core/risk/advanced.py` | 235-257 |
| **Wrong price used** | Bar processing | `core/live/scheduler.py` | 596, 1101, 1164 |
| **Symbol mismatch** | Bar validation | `core/live/scheduler.py` | 394, 596 |
| **Multi-leg not tracking** | Options execution | `core/live/executor_options.py` | 800-900 |
| **Delta hedge wrong size** | Delta hedging | `core/live/delta_hedge_manager.py` | 200-300 |
| **F-string syntax error** | Logging | `core/live/multi_leg_profit_manager.py` | 99 |
| **Options not executing** | Options check | `core/live/scheduler.py` | 1020-1090 |
| **Risk limits too tight** | Risk config | `core/risk/advanced.py` | 14-52 |

---

## 8. DEBUGGING CHECKLIST

When troubleshooting, check in this order:

1. ✅ **Bar Validation**
   - Is `bar.symbol == symbol`?
   - Is `bar.close` correct price?

2. ✅ **Position Sizing**
   - What is `base_investment`? ($1000 default)
   - What is `bar.close`? (should match symbol)
   - What is `adjusted_size` after risk management?
   - What is final `quantity`? (should be ~1-2 shares for $1000 at $670)

3. ✅ **Risk Management**
   - What is `confidence`? (0.0-1.0)
   - What is `regime_type`? (affects caps)
   - What is `regime_cap_pct`? (5% compression, 15% trend)
   - Is `max_size_by_regime` in dollars? (should be, not shares)

4. ✅ **Execution**
   - Did order get submitted?
   - Did fill occur?
   - What is `filled_quantity`?

5. ✅ **Portfolio Update**
   - Did position update correctly?
   - Is `unrealized_pnl` correct?

---

## 9. LOG MESSAGES TO WATCH FOR

```
🔍 [TradeExecution] Executing trade for {symbol}: bar.symbol={bar.symbol}, bar.close=${bar.close:.2f}
✅ [TradeExecution] Trade executed: {symbol} {side} {quantity:.4f} @ ${price:.2f}
🚨 [LiveLoop] SYMBOL MISMATCH: Requested {symbol} but bar has symbol {bar.symbol}!
⚠️ [RiskManager] Position size capped by regime limit
📊 [MultiLegProfit] Tracking {strategy} position: {multi_leg_id}
[DeltaHedge] Executing hedge: {symbol} {side} {hedge_shares} shares
```

---

## 10. CONFIGURATION POINTS

| Config | Location | Default | Effect |
|--------|----------|---------|--------|
| `fixed_investment_amount` | `core/live/scheduler.py` | $1000 | Base position size |
| `compression_max_position_pct` | `core/risk/advanced.py` | 5% | Max size in compression |
| `trend_max_position_pct` | `core/risk/advanced.py` | 15% | Max size in trend |
| `max_symbol_exposure_pct` | `core/risk/advanced.py` | 20% | Max per symbol |
| `testing_mode` | `core/live/scheduler.py` | False | Simpler sizing if True |

---

## Next Steps

1. Use this flowchart to trace where issues occur
2. Add logging at each checkpoint
3. Check the "Key Troubleshooting Points" section for common bugs
4. Use the "Debugging Checklist" to systematically verify each step

