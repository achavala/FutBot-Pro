#!/bin/bash
# Start server for Phase 1 validation

echo "============================================================"
echo "PHASE 1: SIMULATION VALIDATION - STARTING SERVER"
echo "============================================================"
echo ""

# Clean up any existing processes
echo "🧹 Cleaning up existing processes..."
pkill -f uvicorn 2>/dev/null
pkill -f "python.*main.py" 2>/dev/null
sleep 2

# Check if port 8000 is free
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️ Port 8000 is still in use. Killing process..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null
    sleep 1
fi

echo "✅ Cleanup complete"
echo ""

# Start server
echo "🚀 Starting FutBot server..."
echo "   Dashboard: http://localhost:8000/dashboard"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "📋 Next Steps:"
echo "   1. Open dashboard in browser"
echo "   2. Click 'Start Live' or use 'Simulate' button"
echo "   3. Monitor logs for multi-leg execution"
echo "   4. Check Analytics → Options Dashboard for positions"
echo ""
echo "Press Ctrl+C to stop the server"
echo "============================================================"
echo ""

cd /Users/chavala/FutBot

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "🔧 Activating virtual environment..."
    source .venv/bin/activate
elif [ -d "venv" ]; then
    echo "🔧 Activating virtual environment..."
    source venv/bin/activate
fi

# Verify uvicorn is available
if ! python3 -c "import uvicorn" 2>/dev/null; then
    echo "❌ Error: uvicorn not found. Installing dependencies..."
    pip install -q -r requirements.txt
fi

# Start server
python3 main.py --mode api --port 8000

