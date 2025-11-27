#!/usr/bin/env python3
"""Quick script to test IBKR connection."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.live import IBKRBrokerClient


def main():
    """Test IBKR connection."""
    print("🔌 Testing IBKR Connection")
    print("=" * 40)
    print()

    # Try common IBKR ports
    ports = [
        (4002, "TWS/Gateway Default"),
        (7497, "Paper Trading"),
        (7496, "Live Trading"),
        (4001, "TWS Alternative"),
    ]

    for port, name in ports:
        print(f"Trying {name} (port {port})...")
        try:
            client = IBKRBrokerClient(host="127.0.0.1", port=port, client_id=999)
            if client.connect():
                print(f"✅ Connected to {name}!")
                print()

                # Get account info
                account = client.get_account()
                print(f"Account Information:")
                print(f"  Cash: ${account.cash:,.2f}")
                print(f"  Equity: ${account.equity:,.2f}")
                print(f"  Buying Power: ${account.buying_power:,.2f}")
                print()

                # Get positions
                positions = client.get_positions()
                if positions:
                    print(f"Current Positions ({len(positions)}):")
                    for pos in positions:
                        print(f"  {pos.symbol}: {pos.quantity} @ ${pos.avg_entry_price:.2f}")
                else:
                    print("No open positions")
                print()

                client.disconnect()
                print("✅ Connection test successful!")
                return 0
            else:
                print(f"❌ Failed to connect to {name}")
        except Exception as e:
            print(f"❌ Error: {e}")
        print()

    print("❌ Could not connect to IBKR")
    print()
    print("Troubleshooting:")
    print("  1. Ensure IB Gateway or TWS is running")
    print("  2. Check that API is enabled in TWS/Gateway settings")
    print("  3. Verify the correct port (7497 for paper, 7496 for live)")
    print("  4. Check firewall settings")
    return 1


if __name__ == "__main__":
    sys.exit(main())

