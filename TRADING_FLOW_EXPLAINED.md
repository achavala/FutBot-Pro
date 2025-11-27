# Trading Flow & Component Verification Guide

## When Does the Bot Take Trades?

### Complete Decision Flow

```
1. Bar Arrives (every 1 minute)
   ↓
2. Collect 50+ bars (minimum for reliable features)
   ↓
3. Compute Features
   - EMA, SMA, RSI, ATR, ADX, VWAP
   - Hurst exponent, regression slope, IV proxy
   - Detect FVGs (Fair Value Gaps)
   ↓
4. Classify Regime
   - RegimeEngine analyzes features
   - Outputs: regime_type, trend_direction, volatility_level, bias, confidence
   ↓
5. Agents Evaluate
   - TrendAgent: checks if regime is TREND + confidence threshold
   - MeanReversionAgent: checks if regime is MEAN_REVERSION + confidence
   - VolatilityAgent: checks if regime is EXPANSION
   - FVGAgent: checks if active FVG exists + price near midpoint
   ↓
6. Controller Filters & Scores
   - Filters: regime compatibility, confidence minimums, direction conflicts
   - Scores: agent_weight × regime_weight × volatility_weight × confidence
   ↓
7. Risk Manager Check
   - Advanced risk: daily loss limits, drawdown limits, circuit breakers
   - Position sizing: volatility scaling, regime-aware caps
   ↓
8. Execute Trade (if all checks pass)
   - Submit order to IBKR
   - Track position
   - Update portfolio
```

## Trade Execution Conditions

A trade executes when **ALL** of these are true:

1. ✅ **50+ bars collected** (for reliable features)
2. ✅ **Regime confidence ≥ 0.4** (configurable threshold)
3. ✅ **At least one agent produces valid intent** (matches regime)
4. ✅ **Controller confidence ≥ 0.4** (after filtering/scoring)
5. ✅ **Risk manager allows trading** (no kill switch, within limits)
6. ✅ **Position delta ≠ 0** (non-zero trade size)

## Component Verification

### Run Tests

```bash
# Test all components in isolation
python3 scripts/test_trading_components.py

# Diagnose live bot status
python3 scripts/diagnose_trading_flow.py

# Monitor real-time
./scripts/monitor_bot.sh
```

### What Each Test Verifies

1. **RegimeEngine**: Correctly classifies trend vs mean-reversion regimes
2. **Agents**: 
   - Return intents in correct regimes
   - Don't trade in wrong regimes
   - Respect confidence thresholds
3. **Controller**: 
   - Filters invalid intents
   - Scores correctly
   - Vetoes low confidence
   - Blends close scores
4. **Full Pipeline**: Feature computation works end-to-end

## How to Verify Components Are Working

### 1. Check Live Status

```bash
curl http://localhost:8000/live/status
```

Look for:
- `bar_count >= 50` (ready to trade)
- `is_running: true`
- `error: null`

### 2. Check Regime Classification

```bash
curl http://localhost:8000/regime
```

Should show current regime type, confidence, trend direction

### 3. Check Agent Fitness

```bash
curl http://localhost:8000/agents
```

Shows which agents are active and their weights

### 4. Check Risk Status

```bash
curl http://localhost:8000/risk-status
```

Verify `can_trade: true` and no kill switch engaged

### 5. Monitor Logs

```bash
tail -f logs/trading_events.jsonl
```

Watch for regime flips, weight changes, trade executions

## Decision Points That Prevent Trades

### Early Vetoes (No Trade)

1. **Regime Confidence Too Low**
   - `signal.confidence < 0.4` → Controller returns empty decision
   - Reason: "Regime confidence below threshold"

2. **No Agent Signals**
   - Agents don't match current regime → No intents
   - Reason: "No valid agent signals"

3. **Agent Confidence Too Low**
   - Agent confidence < agent's `min_confidence` → Returns empty list
   - Example: TrendAgent needs ≥ 0.6 confidence

4. **Filter Rejection**
   - Intent filtered out (wrong regime, conflict, etc.)
   - Reason logged in controller

5. **Risk Manager Veto**
   - Daily loss limit hit
   - Drawdown limit exceeded
   - Circuit breaker active
   - Reason: "Risk veto: [reason]"

### Final Checks Before Execution

1. **Controller Confidence**
   - Final score < 0.4 → No trade
   - Reason: "Confidence below threshold"

2. **Position Delta**
   - After risk sizing: delta = 0 → No trade
   - Reason: "No position change needed"

## Summary

### What I Created

1. ✅ **`scripts/test_trading_components.py`** - Unit tests for all components
2. ✅ **`scripts/diagnose_trading_flow.py`** - Live bot diagnostic
3. ✅ **`TRADING_FLOW_EXPLAINED.md`** - This document

### How It Works

The bot uses a **deterministic decision tree**:

```
Bar → Features → Regime → Agents → Controller → Risk → Execute
```

Each step can veto the trade, ensuring only high-quality signals execute.

### Verification Commands

```bash
# Test components
python3 scripts/test_trading_components.py

# Check live bot
python3 scripts/diagnose_trading_flow.py

# Monitor continuously
./scripts/monitor_bot.sh
```

All components are verified by design - trades only execute when conditions align!

