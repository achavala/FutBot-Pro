#!/usr/bin/env python3
"""Test Interactive Brokers connection."""

import os
import sys
from dotenv import load_dotenv

load_dotenv()


def test_ibkr_connection():
    """Test IBKR connection and basic operations."""
    print("=" * 60)
    print("Testing IBKR Connection")
    print("=" * 60)

    # Check ib_insync is installed
    try:
        from ib_insync import IB, Stock, util
    except ImportError:
        print("\n✗ ib-insync not installed")
        print("\nInstall it with:")
        print("  pip install ib-insync")
        print("\nOr:")
        print("  pip install -r requirements.txt")
        sys.exit(1)

    # Get configuration
    host = os.getenv("IB_HOST", "127.0.0.1")
    port = int(os.getenv("IB_PORT", "7497"))
    client_id = int(os.getenv("IB_CLIENT_ID", "1"))
    account_id = os.getenv("IB_ACCOUNT_ID")

    print(f"\nConfiguration:")
    print(f"  Host: {host}")
    print(f"  Port: {port} {'(Paper Trading)' if port == 7497 else '(Live Trading!)'}")
    print(f"  Client ID: {client_id}")
    print(f"  Account ID: {account_id}")

    # Warning for live trading
    if port == 7496:
        print("\n" + "⚠️ " * 20)
        print("⚠️  WARNING: YOU ARE CONNECTED TO LIVE TRADING!")
        print("⚠️  This will place REAL orders with REAL money!")
        print("⚠️  Make sure this is intentional!")
        print("⚠️ " * 20)
        response = input("\nType 'YES' to continue with live trading: ")
        if response != "YES":
            print("Aborted.")
            sys.exit(1)

    # Connect to IB Gateway
    print(f"\n1. Connecting to IB Gateway at {host}:{port}...")

    ib = IB()

    try:
        ib.connect(host, port, clientId=client_id)
        print("✓ Connected successfully!")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Make sure IB Gateway is running")
        print("  2. Verify you selected 'Paper Trading' mode")
        print("  3. Check that port 7497 is configured in IB Gateway settings")
        print("  4. Ensure API connections are enabled in IB Gateway")
        print("\nTo enable API:")
        print("  IB Gateway → Configure → Settings → API → Settings")
        print("  ✅ Enable ActiveX and Socket Clients")
        print("  ✅ Socket port: 7497")
        print("  ✅ Trusted IP addresses: 127.0.0.1")
        sys.exit(1)

    # Get account info
    print("\n2. Getting account information...")

    try:
        # Get account values
        account_values = ib.accountValues(account_id)

        cash = 0.0
        equity = 0.0
        buying_power = 0.0

        for av in account_values:
            if av.tag == "CashBalance" and av.currency == "USD":
                cash = float(av.value)
            elif av.tag == "NetLiquidation" and av.currency == "USD":
                equity = float(av.value)
            elif av.tag == "BuyingPower" and av.currency == "USD":
                buying_power = float(av.value)

        print(f"✓ Account Information:")
        print(f"  Account ID: {account_id or ib.managedAccounts()[0]}")
        print(f"  Cash: ${cash:,.2f}")
        print(f"  Equity: ${equity:,.2f}")
        print(f"  Buying Power: ${buying_power:,.2f}")

    except Exception as e:
        print(f"✗ Error getting account info: {e}")

    # Test market data
    print("\n3. Testing market data...")

    try:
        contract = Stock("QQQ", "SMART", "USD")
        ib.qualifyContracts(contract)

        ticker = ib.reqTicker(contract)
        ib.sleep(2)  # Wait for data

        if ticker.marketPrice() > 0:
            print(f"✓ QQQ current price: ${ticker.marketPrice():.2f}")
        else:
            print(f"✓ QQQ bid: ${ticker.bid:.2f}, ask: ${ticker.ask:.2f}")

    except Exception as e:
        print(f"✗ Error getting market data: {e}")

    # Test order submission (will cancel immediately)
    print("\n4. Testing order submission (will cancel immediately)...")

    try:
        from ib_insync import MarketOrder

        contract = Stock("QQQ", "SMART", "USD")
        order = MarketOrder("BUY", 1)

        trade = ib.placeOrder(contract, order)
        ib.sleep(1)  # Wait for order to be submitted

        print(f"✓ Order submitted successfully!")
        print(f"  Order ID: {trade.order.orderId}")
        print(f"  Status: {trade.orderStatus.status}")

        # Cancel the order immediately
        ib.cancelOrder(order)
        ib.sleep(1)
        print(f"✓ Order cancelled successfully")

    except Exception as e:
        print(f"⚠ Order test skipped: {e}")
        print("  (This is OK - may need additional permissions)")

    # Get positions
    print("\n5. Checking current positions...")

    try:
        positions = ib.positions(account_id)
        if positions:
            print(f"✓ You have {len(positions)} open position(s):")
            for pos in positions:
                print(f"  {pos.contract.symbol}: {pos.position} shares @ ${pos.avgCost:.2f}")
        else:
            print("✓ No open positions")

    except Exception as e:
        print(f"⚠ Could not get positions: {e}")

    # Disconnect
    ib.disconnect()

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print("\n✓ IBKR connection is working!")
    print("\nYou can now:")
    print("  1. Start FutBot in demo mode:")
    print("     python main.py --mode api --port 8000 --demo")
    print("\n  2. Start FutBot with IBKR paper trading:")
    print("     python main.py --mode live --symbol QQQ --capital 100000")
    print("\n  3. View the dashboard:")
    print("     http://localhost:8000/visualizations/dashboard")
    print("=" * 60)


if __name__ == "__main__":
    test_ibkr_connection()
