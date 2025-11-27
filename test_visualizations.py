#!/usr/bin/env python3
"""Test script to populate bot manager with sample data for visualization testing."""

import sys
from datetime import datetime, timedelta
import numpy as np

from core.agents.fvg_agent import FVGAgent
from core.agents.mean_reversion_agent import MeanReversionAgent
from core.agents.trend_agent import TrendAgent
from core.agents.volatility_agent import VolatilityAgent
from core.policy.controller import MetaPolicyController
from core.policy.types import FinalTradeIntent
from core.policy_adaptation.adaptor import PolicyAdaptor
from core.portfolio.manager import PortfolioManager
from core.regime.engine import RegimeEngine
from core.regime.types import Bias, RegimeSignal, RegimeType, TrendDirection, VolatilityLevel
from core.reward.memory import RollingMemoryStore
from core.reward.tracker import RewardTracker
from core.risk.manager import RiskManager
from ui.bot_manager import BotManager


def create_sample_signal(bar_idx: int) -> RegimeSignal:
    """Create a sample regime signal."""
    # Rotate through regimes
    regimes = [RegimeType.TREND, RegimeType.MEAN_REVERSION, RegimeType.COMPRESSION, RegimeType.EXPANSION]
    regime = regimes[bar_idx % len(regimes)]

    return RegimeSignal(
        timestamp=datetime.now(),
        trend_direction=TrendDirection.UP if bar_idx % 2 == 0 else TrendDirection.DOWN,
        volatility_level=VolatilityLevel.MEDIUM,
        regime_type=regime,
        bias=Bias.LONG if bar_idx % 3 == 0 else Bias.SHORT,
        confidence=0.7 + (bar_idx % 10) * 0.03,
        active_fvg=None,
        metrics={},
        is_valid=True,
    )


def create_sample_intent(bar_idx: int) -> FinalTradeIntent:
    """Create a sample trade intent."""
    agents = ["trend_agent", "mean_reversion_agent", "volatility_agent", "fvg_agent"]

    return FinalTradeIntent(
        position_delta=0.5 * (1 if bar_idx % 2 == 0 else -1),
        confidence=0.6 + (bar_idx % 10) * 0.04,
        primary_agent=agents[bar_idx % len(agents)],
        contributing_agents=[agents[bar_idx % len(agents)]],
        reason="sample_trade",
        is_valid=True,
    )


def populate_portfolio_with_sample_data(portfolio: PortfolioManager, num_bars: int = 100):
    """Populate portfolio with sample equity curve."""
    print(f"Generating {num_bars} bars of sample data...")

    current_price = 400.0  # QQQ starting price

    for i in range(num_bars):
        # Random walk with slight upward drift
        price_change = np.random.randn() * 2.0 + 0.1
        current_price += price_change
        current_price = max(current_price, 350.0)  # Floor

        portfolio.update_position("QQQ", current_price)
        portfolio.record_equity(current_price)

        # Occasionally create trades
        if i % 10 == 0 and i > 0:
            if np.random.rand() > 0.5:
                portfolio.add_position("QQQ", 10, current_price, datetime.now() - timedelta(days=i))
            elif "QQQ" in portfolio.positions:
                portfolio.close_position("QQQ", current_price, datetime.now(), "sample_exit", "sample_agent")

    print(f"✓ Generated {len(portfolio.equity_curve)} equity curve points")
    print(f"✓ Created {len(portfolio.trade_history)} sample trades")


def main():
    """Main test function."""
    print("=" * 60)
    print("FutBot Visualization Test")
    print("=" * 60)

    # Create components
    agents = [
        TrendAgent(symbol="QQQ"),
        MeanReversionAgent(symbol="QQQ"),
        VolatilityAgent(symbol="QQQ"),
        FVGAgent(symbol="QQQ"),
    ]
    regime_engine = RegimeEngine()
    portfolio = PortfolioManager(100000.0, "QQQ")
    risk_manager = RiskManager(100000.0)
    memory_store = RollingMemoryStore()
    reward_tracker = RewardTracker(memory_store=memory_store)
    adaptor = PolicyAdaptor(memory_store=memory_store)
    controller = MetaPolicyController(adaptor=adaptor)

    # Create bot manager
    bot_manager = BotManager(
        agents=agents,
        regime_engine=regime_engine,
        controller=controller,
        portfolio=portfolio,
        risk_manager=risk_manager,
        reward_tracker=reward_tracker,
        adaptor=adaptor,
    )

    print("\n1. Populating portfolio with sample data...")
    populate_portfolio_with_sample_data(portfolio, num_bars=200)

    print("\n2. Simulating regime changes and agent updates...")
    for i in range(100):
        signal = create_sample_signal(i)
        intent = create_sample_intent(i)
        bot_manager.update_state(signal, intent)

        # Simulate some rewards for agent fitness
        if i % 5 == 0:
            for agent in agents:
                reward = np.random.randn() * 0.1
                memory_store.update_agent(agent.name, reward)

    print(f"✓ Simulated {bot_manager.state.bar_count} bars")
    print(f"✓ Tracked {len(bot_manager.regime_history)} regime observations")

    print("\n3. Summary:")
    print(f"   - Portfolio value: ${portfolio.equity_curve[-1]:,.2f}")
    print(f"   - Total return: {portfolio.get_total_return_pct():.2f}%")
    print(f"   - Max drawdown: {portfolio.get_max_drawdown():.2f}%")
    print(f"   - Total trades: {len(portfolio.trade_history)}")

    print("\n4. Agent fitness:")
    fitness_map = bot_manager.get_agent_fitness()
    for agent_name, fitness in fitness_map.items():
        print(f"   - {agent_name}: {fitness['short_term']:.3f}")

    print("\n5. Regime distribution:")
    regime_dist = bot_manager.get_regime_distribution()
    for regime, count in regime_dist.items():
        print(f"   - {regime}: {count} bars")

    print("\n" + "=" * 60)
    print("✓ Sample data generation complete!")
    print("=" * 60)
    print("\nNow start the API server:")
    print("  python main.py --mode api --port 8000")
    print("\nThen open in browser:")
    print("  http://localhost:8000/visualizations/dashboard")
    print("=" * 60)


if __name__ == "__main__":
    main()
