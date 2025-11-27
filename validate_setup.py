#!/usr/bin/env python3
"""Validate API keys and environment setup."""

import os
import sys
from dotenv import load_dotenv


def print_status(check_name: str, passed: bool, message: str = ""):
    """Print check status with color."""
    if passed:
        print(f"✓ {check_name}")
        if message:
            print(f"  → {message}")
    else:
        print(f"✗ {check_name}")
        if message:
            print(f"  → {message}")


def check_env_file():
    """Check if .env file exists."""
    if not os.path.exists(".env"):
        print("=" * 60)
        print("⚠️  .env file not found!")
        print("=" * 60)
        print("\nPlease create your .env file:")
        print("  1. Copy .env.example to .env")
        print("     cp .env.example .env")
        print("\n  2. Edit .env and add your API keys")
        print("     nano .env")
        print("\n  3. Run this script again")
        print("     python validate_setup.py")
        print("=" * 60)
        return False
    return True


def check_required_vars():
    """Check required environment variables."""
    load_dotenv()

    required_vars = {
        "POLYGON_API_KEY": "Polygon.io API key (get from https://polygon.io/)",
        "ALPACA_API_KEY": "Alpaca API key (get from https://alpaca.markets/)",
        "ALPACA_SECRET_KEY": "Alpaca secret key",
        "ALPACA_BASE_URL": "Alpaca API URL",
    }

    all_present = True
    for var, description in required_vars.items():
        value = os.getenv(var)
        if not value or value.startswith("your_"):
            print_status(f"{var}", False, f"Missing: {description}")
            all_present = False
        else:
            masked_value = value[:8] + "..." if len(value) > 8 else "***"
            print_status(f"{var}", True, masked_value)

    return all_present


def test_polygon():
    """Test Polygon.io connection."""
    try:
        from polygon import RESTClient

        api_key = os.getenv("POLYGON_API_KEY")
        if not api_key or api_key.startswith("your_"):
            print_status("Polygon.io connection", False, "API key not configured")
            return False

        client = RESTClient(api_key)
        # Try to get a quote
        quote = client.get_last_quote("QQQ")
        print_status(
            "Polygon.io connection",
            True,
            f"Connected! QQQ last bid: ${quote.bid_price if hasattr(quote, 'bid_price') else 'N/A'}",
        )
        return True
    except ImportError:
        print_status("Polygon.io connection", False, "polygon-api-client not installed. Run: pip install polygon-api-client")
        return False
    except Exception as e:
        print_status("Polygon.io connection", False, f"Error: {str(e)[:60]}")
        return False


def test_alpaca():
    """Test Alpaca connection."""
    try:
        from alpaca.trading.client import TradingClient

        api_key = os.getenv("ALPACA_API_KEY")
        secret_key = os.getenv("ALPACA_SECRET_KEY")

        if not api_key or api_key.startswith("your_"):
            print_status("Alpaca connection", False, "API keys not configured")
            return False

        # Check if using paper trading
        base_url = os.getenv("ALPACA_BASE_URL", "")
        is_paper = "paper" in base_url.lower()

        client = TradingClient(api_key, secret_key, paper=is_paper)
        account = client.get_account()

        mode = "PAPER" if is_paper else "LIVE"
        print_status(
            f"Alpaca connection ({mode})",
            True,
            f"Account: {account.account_number}, Cash: ${float(account.cash):,.2f}",
        )

        if not is_paper:
            print("\n⚠️  WARNING: You are connected to LIVE trading!")
            print("   Make sure this is intentional. Use paper trading for testing.\n")

        return True
    except ImportError:
        print_status("Alpaca connection", False, "alpaca-py not installed. Run: pip install alpaca-py")
        return False
    except Exception as e:
        print_status("Alpaca connection", False, f"Error: {str(e)[:60]}")
        return False


def check_dependencies():
    """Check if required packages are installed."""
    required_packages = {
        "numpy": "NumPy",
        "pandas": "Pandas",
        "fastapi": "FastAPI",
        "uvicorn": "Uvicorn",
        "matplotlib": "Matplotlib",
        "plotly": "Plotly",
        "pydantic": "Pydantic",
        "yaml": "PyYAML",
        "dotenv": "python-dotenv",
    }

    all_installed = True
    for package, name in required_packages.items():
        try:
            __import__(package)
            print_status(f"{name}", True)
        except ImportError:
            print_status(f"{name}", False, f"Not installed. Run: pip install {package}")
            all_installed = False

    return all_installed


def main():
    """Main validation function."""
    print("=" * 60)
    print("FutBot Setup Validation")
    print("=" * 60)

    # Check .env file exists
    print("\n1. Checking .env file...")
    if not check_env_file():
        sys.exit(1)

    # Check required variables
    print("\n2. Checking environment variables...")
    env_vars_ok = check_required_vars()

    # Check dependencies
    print("\n3. Checking Python packages...")
    deps_ok = check_dependencies()

    # Test API connections
    print("\n4. Testing API connections...")
    polygon_ok = test_polygon()
    alpaca_ok = test_alpaca()

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    all_ok = env_vars_ok and deps_ok and polygon_ok and alpaca_ok

    if all_ok:
        print("✓ All checks passed!")
        print("\nYou're ready to start trading!")
        print("\nNext steps:")
        print("  1. Start in demo mode:")
        print("     python main.py --mode api --port 8000 --demo")
        print("\n  2. Or start paper trading:")
        print("     python main.py --mode live --symbol QQQ --capital 100000")
        print("\n  3. Open the dashboard:")
        print("     http://localhost:8000/visualizations/dashboard")
    else:
        print("✗ Some checks failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("  - Missing dependencies: pip install -r requirements.txt")
        print("  - Missing API keys: Edit .env and add your keys")
        print("  - Invalid API keys: Check your Polygon/Alpaca dashboards")

    print("=" * 60)

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
