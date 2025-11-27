from __future__ import annotations

import pytest

from core.agents.fvg_agent import FVGAgent
from core.agents.mean_reversion_agent import MeanReversionAgent
from core.agents.trend_agent import TrendAgent
from core.agents.volatility_agent import VolatilityAgent
from core.policy.controller import MetaPolicyController
from core.policy_adaptation.adaptor import PolicyAdaptor
from core.portfolio.manager import PortfolioManager
from core.regime.engine import RegimeEngine
from core.regime.types import RegimeType, TrendDirection, VolatilityLevel
from core.reward.memory import RollingMemoryStore
from core.reward.tracker import RewardTracker
from core.risk.manager import RiskManager
from ui.bot_manager import BotManager


@pytest.fixture
def bot_manager():
    """Create a bot manager for testing."""
    agents = [
        TrendAgent(symbol="QQQ"),
        MeanReversionAgent(symbol="QQQ"),
        VolatilityAgent(symbol="QQQ"),
        FVGAgent(symbol="QQQ"),
    ]
    regime_engine = RegimeEngine()
    controller = MetaPolicyController()
    portfolio = PortfolioManager(100000.0, "QQQ")
    risk_manager = RiskManager(100000.0)
    memory_store = RollingMemoryStore()
    reward_tracker = RewardTracker(memory_store=memory_store)
    adaptor = PolicyAdaptor(memory_store=memory_store)

    return BotManager(
        agents=agents,
        regime_engine=regime_engine,
        controller=controller,
        portfolio=portfolio,
        risk_manager=risk_manager,
        reward_tracker=reward_tracker,
        adaptor=adaptor,
    )


def test_bot_manager_start_stop(bot_manager: BotManager):
    """Test starting and stopping the bot."""
    assert not bot_manager.state.is_running
    bot_manager.start()
    assert bot_manager.state.is_running
    bot_manager.stop()
    assert not bot_manager.state.is_running


def test_bot_manager_pause_resume(bot_manager: BotManager):
    """Test pausing and resuming the bot."""
    bot_manager.start()
    assert not bot_manager.state.is_paused
    bot_manager.pause()
    assert bot_manager.state.is_paused
    bot_manager.resume()
    assert not bot_manager.state.is_paused


def test_bot_manager_kill_switch(bot_manager: BotManager):
    """Test kill switch functionality."""
    bot_manager.engage_kill_switch()
    assert bot_manager.risk_manager.kill_switch_engaged
    assert not bot_manager.state.is_running

    bot_manager.disengage_kill_switch()
    assert not bot_manager.risk_manager.kill_switch_engaged


def test_get_portfolio_stats(bot_manager: BotManager):
    """Test getting portfolio statistics."""
    stats = bot_manager.get_portfolio_stats()
    assert "initial_capital" in stats
    assert "current_capital" in stats
    assert "total_return_pct" in stats
    assert stats["initial_capital"] == 100000.0


def test_get_agent_fitness(bot_manager: BotManager):
    """Test getting agent fitness metrics."""
    fitness = bot_manager.get_agent_fitness()
    assert "trend_agent" in fitness
    assert "short_term" in fitness["trend_agent"]
    assert "long_term" in fitness["trend_agent"]
    assert "current_weight" in fitness["trend_agent"]


def test_get_regime_performance(bot_manager: BotManager):
    """Test getting regime performance metrics."""
    performance = bot_manager.get_regime_performance()
    assert RegimeType.TREND.value in performance
    assert "fitness" in performance[RegimeType.TREND.value]
    assert "weight" in performance[RegimeType.TREND.value]


def test_get_risk_status(bot_manager: BotManager):
    """Test getting risk status."""
    status = bot_manager.get_risk_status()
    assert "kill_switch_engaged" in status
    assert "daily_pnl" in status
    assert "can_trade" in status


def test_get_health_status(bot_manager: BotManager):
    """Test getting health status."""
    health = bot_manager.get_health_status()
    assert "is_running" in health
    assert "is_paused" in health
    assert "bar_count" in health
    assert "portfolio_healthy" in health


def test_update_state(bot_manager: BotManager):
    """Test updating bot state."""
    from core.regime.types import RegimeSignal, Bias
    from core.policy.types import FinalTradeIntent

    signal = RegimeSignal(
        timestamp=None,
        trend_direction=TrendDirection.UP,
        volatility_level=VolatilityLevel.MEDIUM,
        regime_type=RegimeType.TREND,
        bias=Bias.LONG,
        confidence=0.8,
    )

    intent = FinalTradeIntent(
        position_delta=0.1,
        confidence=0.8,
        primary_agent="trend_agent",
        contributing_agents=["trend_agent"],
        reason="test",
        is_valid=True,
    )

    bot_manager.update_state(signal, intent)
    assert bot_manager.state.current_regime == signal
    assert bot_manager.state.last_trade_intent == intent
    assert bot_manager.state.bar_count == 1

