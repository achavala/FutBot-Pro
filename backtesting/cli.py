#!/usr/bin/env python3
"""CLI entry point for running backtests."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

from backtesting.runner import BacktestConfig, BacktestRunner
from core.agents.fvg_agent import FVGAgent
from core.agents.mean_reversion_agent import MeanReversionAgent
from core.agents.trend_agent import TrendAgent
from core.agents.volatility_agent import VolatilityAgent
from core.policy.controller import MetaPolicyController
from core.regime.engine import RegimeEngine


def load_data_from_csv(filepath: str) -> pd.DataFrame:
    """Load minute bar data from CSV file."""
    df = pd.read_csv(filepath, index_col=0, parse_dates=True)
    required_cols = ["open", "high", "low", "close", "volume"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")
    return df


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Run backtest on historical data")
    parser.add_argument("--symbol", type=str, default="QQQ", help="Symbol to backtest")
    parser.add_argument("--start", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument("--data", type=str, help="Path to CSV file with minute data")
    parser.add_argument("--capital", type=float, default=100000.0, help="Initial capital")
    parser.add_argument("--output", type=str, help="Output file for results JSON")

    args = parser.parse_args()

    # Load data
    if args.data:
        data = load_data_from_csv(args.data)
    else:
        raise ValueError("--data required: provide path to CSV file with OHLCV data")

    # Filter by date range if provided
    if args.start:
        start_date = datetime.strptime(args.start, "%Y-%m-%d")
        data = data[data.index >= start_date]
    if args.end:
        end_date = datetime.strptime(args.end, "%Y-%m-%d")
        data = data[data.index <= end_date]

    if data.empty:
        print("No data in specified date range")
        return

    # Initialize components
    regime_engine = RegimeEngine()
    controller = MetaPolicyController()

    agents = [
        TrendAgent(symbol=args.symbol),
        MeanReversionAgent(symbol=args.symbol),
        VolatilityAgent(symbol=args.symbol),
        FVGAgent(symbol=args.symbol),
    ]

    # Configure backtest
    config = BacktestConfig(
        initial_capital=args.capital,
        symbol=args.symbol,
        start_date=datetime.strptime(args.start, "%Y-%m-%d") if args.start else None,
        end_date=datetime.strptime(args.end, "%Y-%m-%d") if args.end else None,
    )

    # Run backtest
    runner = BacktestRunner(agents, regime_engine, controller, config)
    print(f"Running backtest on {len(data)} bars...")
    results = runner.run(data)

    # Print results
    print("\n" + "=" * 60)
    print("BACKTEST RESULTS")
    print("=" * 60)
    print(f"Total Return: {results.total_return_pct:.2f}%")
    print(f"Max Drawdown: {results.max_drawdown:.2f}%")
    print(f"Win Rate: {results.win_rate:.2f}%")
    print(f"Sharpe Ratio: {results.sharpe_ratio:.2f}")
    print(f"Total Trades: {results.total_trades}")
    print(f"Final Capital: ${results.final_capital:,.2f}")
    print("=" * 60)

    # Save results if output specified
    if args.output:
        import json

        output_data = {
            "total_return_pct": results.total_return_pct,
            "max_drawdown": results.max_drawdown,
            "win_rate": results.win_rate,
            "sharpe_ratio": results.sharpe_ratio,
            "total_trades": results.total_trades,
            "final_capital": results.final_capital,
            "equity_curve": results.equity_curve,
        }
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()

