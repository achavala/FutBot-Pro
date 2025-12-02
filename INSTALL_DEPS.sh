#!/bin/bash
# Install required dependencies for FutBot

echo "============================================================"
echo "INSTALLING FUTBOT DEPENDENCIES"
echo "============================================================"
echo ""

# Core web server dependencies
echo "📦 Installing core web dependencies..."
pip3 install uvicorn fastapi websockets python-dotenv

# Alpaca trading API
echo ""
echo "📦 Installing Alpaca API..."
pip3 install alpaca-trade-api

# Data processing
echo ""
echo "📦 Installing data processing libraries..."
pip3 install numpy pandas scipy scikit-learn

# HTTP clients
echo ""
echo "📦 Installing HTTP clients..."
pip3 install aiohttp httpx

# Additional utilities
echo ""
echo "📦 Installing utilities..."
pip3 install sqlalchemy uvloop polygon-api-client

echo ""
echo "✅ Installation complete!"
echo ""
echo "Verifying installation..."
echo ""

# Verify core dependencies
python3 -c "import uvicorn; print('✅ uvicorn ok')" || echo "❌ uvicorn failed"
python3 -c "import fastapi; print('✅ fastapi ok')" || echo "❌ fastapi failed"
python3 -c "import alpaca_trade_api; print('✅ alpaca ok')" || echo "⚠️  alpaca not installed (optional)"
python3 -c "import numpy; print('✅ numpy ok')" || echo "❌ numpy failed"
python3 -c "import pandas; print('✅ pandas ok')" || echo "❌ pandas failed"

echo ""
echo "============================================================"
echo "✅ Dependencies installed!"
echo "============================================================"
echo ""
echo "Next: Start server"
echo "  ./START_GAMMA_ONLY.sh"
echo ""

