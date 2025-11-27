# FutBot - Regime-Aware Self-Tuning Trading System

A production-grade, deterministic trading engine that adapts to market regimes using multi-agent decision making and reinforcement-style learning.

## Features

- **Regime Detection**: Classifies market conditions (trend, mean-reversion, compression, expansion)
- **Multi-Agent System**: Specialized agents for different market conditions
- **Meta-Policy Controller**: Intelligently combines agent signals
- **Self-Tuning**: Adaptive weights based on performance
- **Risk Management**: CVaR-based sizing, loss limits, kill switches
- **Backtesting**: Full historical simulation with adaptation
- **Control Panel**: FastAPI-based monitoring and control

## Architecture

```
Data → Features → RegimeEngine → Agents → Meta-Policy → Execution → Reward → Adaptation
```

## Quick Start

### Installation

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt  # If you create one, or install manually:
pip install pandas numpy statsmodels scikit-learn fastapi uvicorn pyyaml pytest
```

### Run Backtest

```bash
# Using the CLI
python -m backtesting.cli --data data/QQQ_1min.csv --start 2024-01-01 --end 2024-06-01 --symbol QQQ

# Or programmatically
python -m backtesting.runner
```

### Start API Server

```bash
# Start the FastAPI control panel
python main.py --mode api --port 8000

# API will be available at:
# - http://localhost:8000/docs (Swagger UI)
# - http://localhost:8000/health (Health check)
```

## API Endpoints

### Control
- `POST /start` - Start the bot
- `POST /stop` - Stop the bot
- `POST /pause` - Pause the bot
- `POST /resume` - Resume the bot
- `POST /kill` - Engage/disengage kill switch

### Monitoring
- `GET /health` - System health status
- `GET /regime` - Current market regime
- `GET /stats` - Portfolio performance statistics
- `GET /agents` - Agent fitness and weights
- `GET /trade-log` - Recent trade history
- `GET /regime-performance` - Performance by regime
- `GET /risk-status` - Risk management status

### Configuration
- `GET /weights` - Current adaptive weights
- `POST /weights/save` - Save weights to config

## Project Structure

```
FutBot/
├── core/
│   ├── agents/          # Trading agents (Trend, MR, Volatility, FVG)
│   ├── features/        # Technical indicators and statistical features
│   ├── regime/          # Regime classification engine
│   ├── policy/          # Meta-policy controller
│   ├── policy_adaptation/  # Adaptive weight evolution
│   ├── portfolio/       # Portfolio management
│   ├── execution/       # Order execution simulation
│   ├── risk/            # Risk management
│   └── reward/          # Reward tracking and memory
├── backtesting/         # Backtesting engine
├── services/            # Data clients (Polygon, Finnhub)
├── ui/                  # FastAPI control panel
├── tests/               # Test suite
└── main.py              # Entry point
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test suite
pytest tests/test_regime_engine.py -v
pytest tests/test_bot_manager.py -v
```

## Configuration

Edit `config/settings.yaml` to configure:
- API keys (Polygon, Finnhub)
- Agent thresholds
- Regime engine parameters
- Risk limits
- Execution parameters

## Development

The system is built with:
- **Python 3.10+**
- **Pandas/NumPy** for data processing
- **Statsmodels** for statistical features
- **FastAPI** for the control panel
- **Pydantic** for type validation

## License

[Your License Here]

## Contributing

[Contributing Guidelines]

