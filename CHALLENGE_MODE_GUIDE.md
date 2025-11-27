# 20-Day Challenge Mode: $1K to $100K

## Overview

This is an **extremely aggressive** trading mode designed to turn $1,000 into $100,000 in 20 trading days. This requires approximately **26% daily returns** (compounded).

⚠️ **WARNING**: This is a very high-risk strategy that can result in significant losses. Only use with capital you can afford to lose entirely.

## Strategy Details

### Target Returns
- **Starting Capital**: $1,000
- **Target Capital**: $100,000
- **Timeframe**: 20 trading days (~4 weeks)
- **Required Daily Return**: ~26% (compounded)
- **Total Return**: 10,000%

### Risk Parameters

**Aggressive Settings:**
- **Profit Target**: 12% per trade
- **Stop Loss**: 6% per trade
- **Leverage**: 3x (options, margin, or crypto)
- **Max Trades/Day**: 5
- **Max Position Size**: 50% of capital (with leverage)
- **Min Confidence**: 0.6

### Trading Strategy

The `ChallengeAgent` uses multiple strategies:

1. **Strong Trends** (70%+ confidence)
   - Long on strong uptrends with bullish bias
   - Short on strong downtrends with bearish bias
   - 3x leverage

2. **Volatility Expansion** (75%+ confidence)
   - Trade with the bias during high volatility
   - 2.4x leverage (slightly less aggressive)

3. **Mean Reversion** (80%+ confidence)
   - Trade against extreme moves
   - 1.8x leverage (most conservative)

4. **Entry Requirements**:
   - High confidence regime (≥0.6)
   - Clear trend or momentum
   - Valid regime signal
   - Not at max trades per day

## Setup

### 1. Enable Challenge Mode

**Via API:**
```bash
curl -X POST http://localhost:8000/challenge/start \
  -H "Content-Type: application/json" \
  -d '{
    "initial_capital": 1000.0,
    "target_capital": 100000.0,
    "trading_days": 20,
    "symbols": ["QQQ", "BTC/USD"],
    "broker_type": "alpaca"
  }'
```

**Via Config:**
Add to `config/settings.yaml`:
```yaml
challenge_mode:
  enabled: true
  initial_capital: 1000.0
  target_capital: 100000.0
  trading_days: 20
  profit_target_pct: 12.0
  stop_loss_pct: 6.0
  leverage_multiplier: 3.0
  max_trades_per_day: 5
```

### 2. Recommended Assets

For maximum volatility and leverage:

**Crypto (Recommended):**
- `BTC/USD` - High volatility, 24/7 trading
- `ETH/USD` - Strong momentum
- Leverage available on most exchanges

**Options (If Available):**
- `QQQ` options - High liquidity
- `SPY` options - Tight spreads
- Requires options trading account

**Equity (Margin):**
- `QQQ` - High volatility ETF
- `SPY` - Broad market exposure
- Requires margin account

### 3. Asset Profiles for Challenge

Update `config/settings.yaml`:
```yaml
symbols:
  BTC/USD:
    asset_type: crypto
    risk_per_trade_pct: 50.0  # Very aggressive
    take_profit_pct: 12.0  # Challenge mode target
    stop_loss_pct: 6.0  # Challenge mode stop
    fixed_investment_amount: null  # Use percentage-based
    exit_on_regime_change: true
    exit_on_bias_flip: true
  
  QQQ:
    asset_type: equity
    risk_per_trade_pct: 50.0
    take_profit_pct: 12.0
    stop_loss_pct: 6.0
    fixed_investment_amount: null
```

## Monitoring

### Check Progress

```bash
curl http://localhost:8000/challenge/status
```

Response:
```json
{
  "status": "active",
  "days_elapsed": 5,
  "days_remaining": 15,
  "start_capital": 1000.0,
  "current_capital": 3200.0,
  "target_capital": 100000.0,
  "progress_pct": 3.2,
  "total_return_pct": 220.0,
  "required_daily_return_pct": 28.5,
  "avg_daily_return_pct": 26.0,
  "win_rate": 65.0,
  "total_trades": 20
}
```

### Dashboard

The challenge progress is displayed on the dashboard:
- Current capital vs target
- Days remaining
- Required daily return
- Win rate
- Trade statistics

## Risk Management

### Key Risks

1. **High Leverage**: 3x leverage means 3x losses too
2. **Rapid Drawdowns**: Can lose 6%+ per trade quickly
3. **Overtrading**: Max 5 trades/day to prevent exhaustion
4. **Market Conditions**: Requires favorable volatility

### Safety Features

- **Stop Loss**: Automatic 6% stop loss
- **Max Trades**: Limited to 5 per day
- **Confidence Threshold**: Only high-confidence trades
- **Regime Filtering**: Only trades in favorable regimes

## Realistic Expectations

### Success Factors

1. **High Win Rate**: Need 60%+ win rate
2. **Favorable Markets**: High volatility periods
3. **Discipline**: Stick to strategy, don't overtrade
4. **Luck**: Some favorable market moves

### Challenges

1. **Compounding**: Need consistent 26% daily returns
2. **Drawdowns**: One bad day can set you back significantly
3. **Market Conditions**: Not all days are favorable
4. **Psychological**: High pressure, high stress

## Example Scenarios

### Scenario 1: Perfect Execution
- Day 1: $1,000 → $1,260 (+26%)
- Day 2: $1,260 → $1,588 (+26%)
- Day 3: $1,588 → $2,001 (+26%)
- ...
- Day 20: $100,000 ✅

### Scenario 2: With Drawdowns
- Day 1-5: Average 20% daily → $2,488
- Day 6: -6% loss → $2,339
- Day 7-10: Average 30% daily → $6,700
- Day 11: -6% loss → $6,298
- Day 12-20: Average 28% daily → $100,000 ✅

### Scenario 3: Failure
- Day 1-3: Good start → $2,000
- Day 4-5: Two losses → $1,760
- Day 6-7: More losses → $1,550
- Day 8: Major loss → $1,200
- **Challenge fails** ❌

## Recommendations

1. **Start Small**: Test with paper trading first
2. **Monitor Closely**: Watch every trade
3. **Be Ready to Stop**: If down 20%+, consider pausing
4. **Use Best Assets**: Crypto or options for volatility
5. **Time It Right**: Start during high volatility periods

## API Endpoints

### Start Challenge
```bash
POST /challenge/start
{
  "initial_capital": 1000.0,
  "target_capital": 100000.0,
  "trading_days": 20,
  "symbols": ["BTC/USD"],
  "broker_type": "alpaca"
}
```

### Check Status
```bash
GET /challenge/status
```

### Stop Challenge
```bash
POST /challenge/stop
```

## Summary

This challenge mode is designed for **experienced traders** who understand:
- High leverage risks
- Options/crypto trading
- Aggressive position sizing
- Rapid profit-taking

**Remember**: This is extremely high risk. Most traders will not achieve this goal. Only use capital you can afford to lose entirely.

Good luck! 🚀💰

