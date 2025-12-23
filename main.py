#!/usr/bin/env python3
"""Main entry point for FutBot trading system."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import uvicorn

from core.factory import create_bot_manager
from ui.bot_manager import BotManager
from ui.fastapi_app import app, set_bot_manager


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="FutBot Trading System")
    parser.add_argument("--mode", choices=["api", "backtest"], default="api", help="Run mode")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="API host")
    parser.add_argument("--port", type=int, default=8000, help="API port")
    parser.add_argument("--symbol", type=str, default="QQQ", help="Trading symbol")
    parser.add_argument("--capital", type=float, default=100000.0, help="Initial capital")
    parser.add_argument("--config", type=str, help="Path to config file")
    parser.add_argument("--demo", action="store_true", help="Load demo data for visualization testing")

    args = parser.parse_args()

    if args.mode == "api":
        # Initialize bot manager
        manager = create_bot_manager(symbol=args.symbol, initial_capital=args.capital)

        # Load demo data if requested
        if args.demo:
            from demo_mode import populate_demo_data

            populate_demo_data(manager)

        set_bot_manager(manager)

        print(f"Starting FutBot API server on {args.host}:{args.port}")
        print(f"API docs available at http://{args.host}:{args.port}/docs")
        print(f"Health check at http://{args.host}:{args.port}/health")
        print(f"Interactive dashboard at http://{args.host}:{args.port}/visualizations/dashboard")

        uvicorn.run(app, host=args.host, port=args.port)

    elif args.mode == "backtest":
        print("Backtest mode - use backtesting CLI instead")
        print("Example: python -m backtesting.cli --data data.csv --start 2024-01-01 --end 2024-06-01")
        sys.exit(1)


if __name__ == "__main__":
    main()

