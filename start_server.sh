#!/bin/bash
# Start FutBot API server with virtual environment

cd "$(dirname "$0")"

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✅ Virtual environment activated"
elif [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "❌ No virtual environment found. Please create one first:"
    echo "   python3 -m venv .venv"
    echo "   source .venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Check if uvicorn is installed
if ! python -c "import uvicorn" 2>/dev/null; then
    echo "⚠️  uvicorn not found, installing..."
    pip install uvicorn fastapi
fi

# Start the server
echo "🚀 Starting FutBot API server..."
python main.py --mode api --port 8000
