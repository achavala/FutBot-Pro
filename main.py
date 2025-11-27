#!/usr/bin/env python3
"""Main entry point for FutBot trading system."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import uvicorn

from core.agents.fvg_agent import FVGAgent
from core.agents.mean_reversion_agent import MeanReversionAgent
from core.agents.trend_agent import TrendAgent
from core.agents.volatility_agent import VolatilityAgent
from core.settings_loader import load_settings
from core.policy.controller import MetaPolicyController
from core.policy_adaptation.adaptor import PolicyAdaptor
from core.portfolio.manager import PortfolioManager
from core.regime.engine import RegimeEngine
from core.reward.memory import RollingMemoryStore
from core.reward.tracker import RewardTracker
from core.risk.advanced import AdvancedRiskConfig, AdvancedRiskManager
from core.risk.manager import RiskConfig, RiskManager
from ui.bot_manager import BotManager
from ui.fastapi_app import app, set_bot_manager


def create_bot_manager(symbol: str = "QQQ", initial_capital: float = 100000.0) -> BotManager:
    """Create and initialize bot manager with all components."""
    # Initialize components
    regime_engine = RegimeEngine()
    controller = MetaPolicyController()

    agents = [
        TrendAgent(symbol=symbol),
        MeanReversionAgent(symbol=symbol),
        VolatilityAgent(symbol=symbol),
        FVGAgent(symbol=symbol),
    ]

    portfolio = PortfolioManager(initial_capital=initial_capital, symbol=symbol)
    risk_manager = RiskManager(initial_capital=initial_capital)
    advanced_risk = AdvancedRiskManager(initial_capital=initial_capital)

    # Reward and adaptation
    memory_store = RollingMemoryStore()
    reward_tracker = RewardTracker(memory_store=memory_store)
    adaptor = PolicyAdaptor(memory_store=memory_store)

    # Update controller with adaptor
    controller = MetaPolicyController(adaptor=adaptor)

    # Create bot manager
    manager = BotManager(
        agents=agents,
        regime_engine=regime_engine,
        controller=controller,
        portfolio=portfolio,
        risk_manager=risk_manager,
        reward_tracker=reward_tracker,
        adaptor=adaptor,
        advanced_risk_manager=advanced_risk,
    )

    return manager


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

