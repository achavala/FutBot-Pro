# 🚀 Quick Start Guide - See Your Visualizations!

## Step 1: Start the Server with Demo Data

```bash
source .venv/bin/activate
python main.py --mode api --port 8000 --demo
```

You should see:
```
📊 Generating 200 bars of demo data...
✓ Generated 200 equity curve points
✓ Created 4 demo trades
✓ Simulated 100 bars
✓ Tracked 100 regime observations

📈 Demo Stats:
   Portfolio value: $100,xxx.xx
   Total return: x.xx%
   Max drawdown: x.xx%

Starting FutBot API server on 0.0.0.0:8000
API docs available at http://0.0.0.0:8000/docs
Health check at http://0.0.0.0:8000/health
Interactive dashboard at http://0.0.0.0:8000/visualizations/dashboard
INFO:     Started server process...
```

## Step 2: Open Your Browser

### 🎯 Best Place to Start: Interactive Dashboard

```
http://localhost:8000/visualizations/dashboard
```

This shows a 2x2 grid with:
- **Top Left**: Equity curve (portfolio value over time)
- **Top Right**: Drawdown chart (risk visualization)
- **Bottom Left**: Agent fitness evolution (which agents are performing well)
- **Bottom Right**: Regime distribution (market condition breakdown)

**Features:**
- Hover over points to see exact values
- Click legend items to show/hide traces
- Zoom by dragging
- Pan by clicking and dragging
- Double-click to reset

---

### 📊 Individual Charts (Static PNGs)

Open these URLs directly in your browser:

#### Equity Curve
```
http://localhost:8000/visualizations/equity-curve
```
Shows your portfolio value over time with total return percentage.

#### Drawdown Chart
```
http://localhost:8000/visualizations/drawdown
```
Shows risk - how much you were down from peak at any point.

#### Agent Fitness Evolution
```
http://localhost:8000/visualizations/agent-fitness
```
Shows which agents (trend, mean-reversion, volatility, FVG) are performing well over time.

#### Regime Distribution
```
http://localhost:8000/visualizations/regime-distribution
```
Pie chart showing what percentage of time the market was in each regime (trend, mean-reversion, compression, expansion).

#### Weight Evolution
```
http://localhost:8000/visualizations/weight-evolution
```
Shows how the adaptive weights changed over time as the system learned.

---

### 🔍 System Status Endpoints (JSON)

#### Health Check
```
http://localhost:8000/health
```
Returns JSON with system health, running status, portfolio health, risk status.

#### Portfolio Stats
```
http://localhost:8000/stats
```
Returns JSON with returns, drawdown, win rate, Sharpe ratio, trade count.

#### Current Regime
```
http://localhost:8000/regime
```
Returns JSON with current market regime classification.

#### Agent Fitness
```
http://localhost:8000/agents
```
Returns JSON with fitness metrics for all agents.

---

### 📚 Interactive API Documentation (Swagger UI)

```
http://localhost:8000/docs
```

This gives you a **web interface** to:
- See all available endpoints
- Try them out interactively
- See request/response schemas
- Test control endpoints (start, stop, pause, kill switch)

---

## Step 3: Try the Control Endpoints

### In Swagger UI (http://localhost:8000/docs)

1. Click on **POST /start**
2. Click "Try it out"
3. Click "Execute"
4. See the bot start running

Or use curl:

```bash
# Start the bot
curl -X POST http://localhost:8000/start -H "Content-Type: application/json" -d '{}'

# Check health
curl http://localhost:8000/health

# Get agent fitness
curl http://localhost:8000/agents

# Engage kill switch
curl -X POST http://localhost:8000/kill -H "Content-Type: application/json" -d '{"engage": true}'
```

---

## Step 4: Save Images

Right-click on any PNG chart and select "Save Image As..." to download.

Or use curl:

```bash
# Download equity curve
curl http://localhost:8000/visualizations/equity-curve > equity_curve.png

# Download all charts
curl http://localhost:8000/visualizations/equity-curve > equity_curve.png
curl http://localhost:8000/visualizations/drawdown > drawdown.png
curl http://localhost:8000/visualizations/agent-fitness > agent_fitness.png
curl http://localhost:8000/visualizations/regime-distribution > regime_distribution.png
curl http://localhost:8000/visualizations/weight-evolution > weight_evolution.png
```

---

## Understanding the Demo Data

The `--demo` flag generates:
- **200 bars** of synthetic equity curve (random walk with drift)
- **100 regime observations** (cycling through all regime types)
- **Agent fitness updates** (random performance for demonstration)
- **4 sample trades** (for trade history visualization)

This lets you see the visualizations working **without running a full backtest**.

---

## Next Steps

### Run a Real Backtest

```bash
python -m backtesting.cli \
  --data data/QQQ_1min.csv \
  --start 2024-01-01 \
  --end 2024-06-01 \
  --symbol QQQ
```

Then start the API to see real results:
```bash
python main.py --mode api --port 8000
```

### Customize the Demo Data

Edit `demo_mode.py` to:
- Change the number of bars
- Adjust price movement volatility
- Control regime distribution
- Modify agent performance patterns

---

## Troubleshooting

### Server won't start
```bash
# Check if port 8000 is already in use
lsof -i :8000

# Use a different port
python main.py --mode api --port 8080 --demo
```

### Charts show "No data available"
Make sure you used the `--demo` flag when starting the server.

### Import errors
```bash
# Make sure virtual environment is activated
source .venv/bin/activate

# Check dependencies
pip list | grep -E "fastapi|matplotlib|plotly|uvicorn"
```

---

## What You're Seeing

- **Equity Curve**: Your trading performance over time
- **Drawdown**: Risk - worst peak-to-trough decline
- **Agent Fitness**: Which strategies are working
- **Regime Distribution**: Market conditions you traded in
- **Weight Evolution**: How the system adapted

These visualizations are **essential** for:
- Debugging strategy issues
- Understanding what's working
- Building confidence before live trading
- Analyzing performance
