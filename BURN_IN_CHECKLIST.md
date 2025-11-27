# Paper Trading Burn-In Checklist

This checklist helps you monitor and validate the trading system during the critical burn-in period (2-4 weeks of market-hours runtime).

## Pre-Market Open (Daily)

- [ ] **System Health Check**
  - [ ] Verify API server is running: `GET /health`
  - [ ] Check live trading status: `GET /live/status`
  - [ ] Confirm no errors in logs: `tail -n 50 logs/futbot.log`
  - [ ] Verify data feed connection is active

- [ ] **Risk Status Review**
  - [ ] Check risk status: `GET /risk-status`
  - [ ] Verify kill switch is in correct state
  - [ ] Confirm daily loss limit is reset (if applicable)
  - [ ] Review advanced risk metrics: `GET /risk-metrics`

- [ ] **Portfolio State**
  - [ ] Review current positions: `GET /live/portfolio`
  - [ ] Check overnight PnL
  - [ ] Verify position sizes are within limits

- [ ] **Configuration Verification**
  - [ ] Confirm position size limits are correct
  - [ ] Verify daily loss limits are set appropriately
  - [ ] Check that advanced risk is enabled

## Mid-Day Check (Optional, but Recommended)

- [ ] **Performance Monitoring**
  - [ ] Check equity curve: `GET /visualizations/equity-curve`
  - [ ] Review drawdown: `GET /visualizations/drawdown`
  - [ ] Monitor recent trades: `GET /live/recent-trades`

- [ ] **Regime & Agent Status**
  - [ ] Check current regime: `GET /regime`
  - [ ] Review agent fitness: `GET /agents`
  - [ ] Monitor weight evolution: `GET /visualizations/weight-evolution`

- [ ] **Event Log Review**
  - [ ] Check for risk events: `grep "risk_event" logs/trading_events.jsonl | tail -20`
  - [ ] Review regime flips: `grep "regime_flip" logs/trading_events.jsonl | tail -20`
  - [ ] Check for outlier PnL: `grep "outlier_pnl" logs/trading_events.jsonl | tail -20`

## End of Day (EOD) Review

- [ ] **Daily Performance Summary**
  - [ ] Review daily PnL: `GET /stats`
  - [ ] Check total return: `GET /stats` → `total_return_pct`
  - [ ] Review max drawdown: `GET /stats` → `max_drawdown`
  - [ ] Check win rate: `GET /stats` → `win_rate`

- [ ] **Risk Metrics Review**
  - [ ] Verify daily loss limit was not exceeded
  - [ ] Check if any circuit breakers triggered
  - [ ] Review drawdown progression
  - [ ] Confirm position sizes stayed within limits

- [ ] **Agent & Regime Analysis**
  - [ ] Review regime distribution: `GET /visualizations/regime-distribution`
  - [ ] Check agent fitness evolution: `GET /visualizations/agent-fitness`
  - [ ] Review weight changes: `GET /weights`
  - [ ] Identify which agents performed best/worst

- [ ] **Event Log Analysis**
  - [ ] Count risk events: `grep -c "risk_event" logs/trading_events.jsonl`
  - [ ] Review all "no_trade" events with high confidence
  - [ ] Check for any critical errors: `grep "critical" logs/trading_events.jsonl`

- [ ] **Trade Review**
  - [ ] Review all trades from the day: `GET /trade-log`
  - [ ] Identify best and worst trades
  - [ ] Check for any execution issues
  - [ ] Verify slippage and commissions are reasonable

- [ ] **System Stability**
  - [ ] Check uptime: `GET /live/status` → `bar_count`
  - [ ] Review error logs for any issues
  - [ ] Verify state was saved: `ls -lh state/live_state.json`

## Weekly Review

- [ ] **Performance Metrics**
  - [ ] Calculate weekly Sharpe ratio
  - [ ] Review weekly return vs. benchmark
  - [ ] Check consistency of performance

- [ ] **Regime Performance**
  - [ ] Review regime performance: `GET /regime-performance`
  - [ ] Identify which regimes were most profitable
  - [ ] Check if regime classification is working correctly

- [ ] **Agent Evolution**
  - [ ] Review weight evolution over the week
  - [ ] Check if any agents are being penalized too heavily
  - [ ] Verify adaptation is working as expected

- [ ] **Risk Review**
  - [ ] Review all risk events from the week
  - [ ] Verify risk controls are working correctly
  - [ ] Check if any adjustments to risk limits are needed

- [ ] **Configuration Review**
  - [ ] Review if any config changes are needed
  - [ ] Document any issues or anomalies
  - [ ] Plan any adjustments for next week

## Red Flags to Watch For

### Immediate Action Required

- [ ] **Daily loss limit exceeded** → Stop trading immediately
- [ ] **Hard drawdown limit hit** → Stop trading immediately
- [ ] **Circuit breaker triggered** → Review recent trades and risk settings
- [ ] **System errors in logs** → Investigate and fix before continuing
- [ ] **Data feed disconnection** → Verify connection and restart if needed

### Warning Signs (Investigate)

- [ ] **Rapid weight swings** → May indicate overfitting or unstable adaptation
- [ ] **One agent dominating** → May need to rebalance agent weights
- [ ] **Frequent "no_trade" events with high confidence** → May indicate risk settings too conservative
- [ ] **Consistent losses in specific regime** → May need to disable agent for that regime
- [ ] **Outlier PnL events** → Review trades for execution issues

### Good Signs

- [ ] **Stable weight evolution** → Adaptation is working smoothly
- [ ] **Risk controls triggering appropriately** → System is protecting capital
- [ ] **Consistent regime classification** → Engine is working correctly
- [ ] **Positive Sharpe ratio** → Strategy is performing well
- [ ] **Low drawdown relative to returns** → Good risk-adjusted performance

## Notes Section

Use this space to document observations, issues, and learnings:

### Week 1
- 

### Week 2
- 

### Week 3
- 

### Week 4
- 

