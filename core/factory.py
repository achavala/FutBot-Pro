from __future__ import annotations

from core.agents.fvg_agent import FVGAgent
from core.agents.mean_reversion_agent import MeanReversionAgent
from core.agents.trend_agent import TrendAgent
from core.agents.volatility_agent import VolatilityAgent
from core.policy.controller import MetaPolicyController
from core.policy_adaptation.adaptor import PolicyAdaptor
from core.portfolio.manager import PortfolioManager
from core.regime.engine import RegimeEngine
from core.reward.memory import RollingMemoryStore
from core.reward.tracker import RewardTracker
from core.risk.advanced import AdvancedRiskManager
from core.risk.manager import RiskManager
from ui.bot_manager import BotManager


def create_bot_manager(symbol: str = "QQQ", initial_capital: float = 100000.0) -> BotManager:
    """Create and initialize bot manager with all components."""
    # Initialize components
    regime_engine = RegimeEngine()
    
    # Initialize memory and adaptor first
    memory_store = RollingMemoryStore()
    adaptor = PolicyAdaptor(memory_store=memory_store)
    
    # Initialize controller with adaptor
    controller = MetaPolicyController(adaptor=adaptor)

    agents = [
        TrendAgent(symbol=symbol),
        MeanReversionAgent(symbol=symbol),
        VolatilityAgent(symbol=symbol),
        FVGAgent(symbol=symbol),
    ]

    portfolio = PortfolioManager(initial_capital=initial_capital, symbol=symbol)
    risk_manager = RiskManager(initial_capital=initial_capital)
    advanced_risk = AdvancedRiskManager(initial_capital=initial_capital)

    reward_tracker = RewardTracker(memory_store=memory_store)

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

