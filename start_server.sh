#!/bin/bash
# Start FutBot API server with virtual environment

cd "$(dirname "$0")"

# Kill any existing processes on port 8000
echo "🛑 Checking for existing processes on port 8000..."
lsof -ti:8000 | xargs kill -9 2>/dev/null
pkill -9 -f "uvicorn" 2>/dev/null
pkill -9 -f "python.*fastapi" 2>/dev/null
pkill -9 -f "python.*main.py" 2>/dev/null
sleep 2

# Verify port is free
if lsof -ti:8000 > /dev/null 2>&1; then
    echo "⚠️  Port 8000 still in use, forcing kill..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null
    sleep 2
fi

if lsof -ti:8000 > /dev/null 2>&1; then
    echo "❌ Cannot free port 8000. Please manually kill the process:"
    lsof -ti:8000 | xargs ps -p
    exit 1
fi

echo "✅ Port 8000 is free"

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
