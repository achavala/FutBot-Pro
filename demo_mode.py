#!/usr/bin/env python3
"""Demo mode - populate bot manager with sample data for visualization testing."""

from datetime import datetime, timedelta
import numpy as np

from core.policy.types import FinalTradeIntent
from core.regime.types import Bias, RegimeSignal, RegimeType, TrendDirection, VolatilityLevel


def populate_demo_data(bot_manager, num_bars: int = 200):
    """Populate bot manager with sample data for demo purposes."""
    print(f"\n📊 Generating {num_bars} bars of demo data...")

    current_price = 400.0  # QQQ starting price
    portfolio = bot_manager.portfolio

    # Generate equity curve
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
                portfolio.close_position("QQQ", current_price, datetime.now(), "demo_exit", "demo_agent")

    # Simulate regime changes and agent updates
    regimes = [RegimeType.TREND, RegimeType.MEAN_REVERSION, RegimeType.COMPRESSION, RegimeType.EXPANSION]
    agents_list = ["trend_agent", "mean_reversion_agent", "volatility_agent", "fvg_agent"]

    for i in range(100):
        # Create sample signal
        signal = RegimeSignal(
            timestamp=datetime.now(),
            trend_direction=TrendDirection.UP if i % 2 == 0 else TrendDirection.DOWN,
            volatility_level=VolatilityLevel.MEDIUM,
            regime_type=regimes[i % len(regimes)],
            bias=Bias.LONG if i % 3 == 0 else Bias.SHORT,
            confidence=0.7 + (i % 10) * 0.03,
            active_fvg=None,
            metrics={},
            is_valid=True,
        )

        # Create sample intent
        intent = FinalTradeIntent(
            position_delta=0.5 * (1 if i % 2 == 0 else -1),
            confidence=0.6 + (i % 10) * 0.04,
            primary_agent=agents_list[i % len(agents_list)],
            contributing_agents=[agents_list[i % len(agents_list)]],
            reason="demo_trade",
            is_valid=True,
        )

        bot_manager.update_state(signal, intent)

        # Simulate some rewards for agent fitness
        if i % 5 == 0:
            for agent in bot_manager.agents:
                reward = np.random.randn() * 0.1
                bot_manager.reward_tracker.memory.update_agent(agent.name, reward)

    print(f"✓ Generated {len(portfolio.equity_curve)} equity curve points")
    print(f"✓ Created {len(portfolio.trade_history)} demo trades")
    print(f"✓ Simulated {bot_manager.state.bar_count} bars")
    print(f"✓ Tracked {len(bot_manager.regime_history)} regime observations")
    print(f"\n📈 Demo Stats:")
    print(f"   Portfolio value: ${portfolio.equity_curve[-1]:,.2f}")
    print(f"   Total return: {portfolio.get_total_return_pct():.2f}%")
    print(f"   Max drawdown: {portfolio.get_max_drawdown():.2f}%\n")
