#!/bin/bash
# IBKR Setup Script for FutBot
# This script helps set up Interactive Brokers for API access

set -e

echo "🔧 FutBot IBKR Setup Script"
echo "============================"
echo ""

# Detect Python and pip commands
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Python is not installed"
    exit 1
fi

# Try to use pip from venv if it exists
if [ -f ".venv/bin/pip" ]; then
    PIP_CMD=".venv/bin/pip"
    echo "✅ Using virtual environment"
elif command -v pip3 &> /dev/null; then
    PIP_CMD="pip3"
elif command -v pip &> /dev/null; then
    PIP_CMD="pip"
else
    echo "❌ pip is not installed"
    exit 1
fi

# Check if Java is installed (required for IB Gateway/TWS)
JAVA_INSTALLED=false
if command -v java &> /dev/null; then
    # Try to get Java version (suppress errors)
    JAVA_VERSION=$(java -version 2>&1 | head -n 1 || echo "")
    if [[ ! "$JAVA_VERSION" =~ "Unable to locate" ]]; then
        JAVA_INSTALLED=true
        echo "✅ Java is installed: $JAVA_VERSION"
    fi
fi

if [ "$JAVA_INSTALLED" = false ]; then
    echo "⚠️  Java runtime not found. IB Gateway/TWS requires Java."
    echo ""
    if command -v brew &> /dev/null; then
        echo "Installing Java via Homebrew..."
        brew install openjdk
        echo "✅ Java installed"
    else
        echo "To install Java on macOS:"
        echo "  brew install openjdk"
        echo ""
        echo "Or download from: https://www.java.com/download/"
        echo ""
        echo "⚠️  Please install Java before using IB Gateway/TWS"
    fi
fi

echo ""

# Check if ib_insync is installed
if $PYTHON_CMD -c "import ib_insync" 2>/dev/null; then
    echo "✅ ib_insync Python package is installed"
else
    echo "📦 Installing ib_insync..."
    $PIP_CMD install ib-insync
    echo "✅ ib_insync installed"
fi

echo ""
echo "📥 Next Steps:"
echo "=============="
echo ""
echo "1. Download IB Gateway (recommended) or TWS:"
echo "   - IB Gateway: https://www.interactivebrokers.com/en/index.php?f=16457"
echo "   - TWS: https://www.interactivebrokers.com/en/index.php?f=16042"
echo ""
echo "2. Install and launch IB Gateway/TWS"
echo ""
echo "3. Configure API settings:"
echo "   - Go to: Configure → API → Settings"
echo "   - Enable 'Enable ActiveX and Socket Clients'"
echo "   - Set Socket port to:"
echo "     * 7497 for paper trading"
echo "     * 7496 for live trading"
echo "   - Add 127.0.0.1 to trusted IPs (optional)"
echo ""
echo "4. Log in with your IBKR account (paper or live)"
echo ""
echo "5. Start FutBot and connect:"
echo "   python main.py --mode api --port 8000"
echo ""
echo "6. Use the /live/start endpoint with broker_type='ibkr'"
echo ""
echo "📚 For detailed instructions, see: docs/IBKR_SETUP.md"
echo ""

