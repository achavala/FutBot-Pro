#!/bin/bash
# Quick Java installation for IBKR

echo "📦 Installing Java for IB Gateway/TWS..."

if command -v brew &> /dev/null; then
    brew install openjdk
    
    # Add to PATH for current session
    export PATH="/opt/homebrew/opt/openjdk/bin:$PATH"
    
    # Add to .zshrc if not already there
    if ! grep -q "openjdk/bin" ~/.zshrc 2>/dev/null; then
        echo 'export PATH="/opt/homebrew/opt/openjdk/bin:$PATH"' >> ~/.zshrc
        echo "✅ Added Java to PATH in ~/.zshrc"
    fi
    
    echo "✅ Java installed!"
    echo ""
    echo "To use Java in this terminal, run:"
    echo "  export PATH=\"/opt/homebrew/opt/openjdk/bin:\$PATH\""
    echo ""
    echo "Or restart your terminal (it's already in ~/.zshrc)"
else
    echo "❌ Homebrew not found. Please install Java manually:"
    echo "   https://www.java.com/download/"
fi

