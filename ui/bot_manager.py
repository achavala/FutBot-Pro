from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)

from core.agents.base import BaseAgent
from core.policy.controller import MetaPolicyController
from core.policy.types import FinalTradeIntent
from core.policy_adaptation.adaptor import PolicyAdaptor
from core.portfolio.manager import PortfolioManager, Trade
from core.regime.engine import RegimeEngine
from core.regime.types import RegimeSignal
from core.reward.memory import RollingMemoryStore
from core.reward.tracker import RewardTracker
from core.live import LiveTradingLoop, LiveTradingConfig, StateStore
from core.live.broker_client import BaseBrokerClient
from core.live.data_feed import BaseDataFeed
from core.live.executor_live import LiveTradeExecutor
from core.logging.events import EventLogger
from core.risk.advanced import AdvancedRiskManager, AdvancedRiskConfig
from core.risk.manager import RiskManager


@dataclass
class BotState:
    """Tracks the current state of the trading bot."""

    is_running: bool = False
    is_paused: bool = False
    current_regime: Optional[RegimeSignal] = None
    last_trade_intent: Optional[FinalTradeIntent] = None
    last_update_time: Optional[datetime] = None
    bar_count: int = 0
    error_message: Optional[str] = None


class BotManager:
    """Orchestrates all components of the trading system."""

    def __init__(
        self,
        agents: Sequence[BaseAgent],
        regime_engine: RegimeEngine,
        controller: MetaPolicyController,
        portfolio: PortfolioManager,
        risk_manager: RiskManager,
        reward_tracker: RewardTracker,
        adaptor: Optional[PolicyAdaptor] = None,
        advanced_risk_manager: Optional[AdvancedRiskManager] = None,
    ):
        self.agents = agents
        self.regime_engine = regime_engine
        self.controller = controller
        self.portfolio = portfolio
        self.risk_manager = risk_manager
        self.reward_tracker = reward_tracker
        self.adaptor = adaptor
        self.advanced_risk = advanced_risk_manager

        self.state = BotState()
        self.recent_trade_intents: List[FinalTradeIntent] = []
        self.max_recent_intents = 50

        # Visualization data tracking
        self.agent_fitness_history: Dict[str, List[float]] = {agent.name: [] for agent in agents}
        self.weight_history: Dict[str, List[float]] = {}
        self.regime_history: List[str] = []

        # Live trading components
        self.live_loop: Optional[LiveTradingLoop] = None
        self.broker_client: Optional[BaseBrokerClient] = None
        self.data_feed: Optional[BaseDataFeed] = None
        self.live_executor: Optional[LiveTradeExecutor] = None
        self.state_store: Optional[StateStore] = None
        self.mode: str = "backtest"  # "backtest" or "live"

        # Event logging
        self.event_logger: Optional[EventLogger] = None

    def start(self) -> None:
        """Start the bot."""
        if self.state.is_running:
            raise ValueError("Bot is already running")
        self.state.is_running = True
        self.state.is_paused = False
        self.state.error_message = None

    def stop(self) -> None:
        """Stop the bot."""
        self.state.is_running = False
        self.state.is_paused = False

    def pause(self) -> None:
        """Pause the bot (keeps state but stops processing)."""
        if not self.state.is_running:
            raise ValueError("Bot is not running")
        self.state.is_paused = True

    def resume(self) -> None:
        """Resume the bot."""
        if not self.state.is_running:
            raise ValueError("Bot is not running")
        self.state.is_paused = False

    def engage_kill_switch(self) -> None:
        """Engage emergency kill switch."""
        self.risk_manager.engage_kill_switch()
        self.stop()

    def disengage_kill_switch(self) -> None:
        """Disengage kill switch."""
        self.risk_manager.disengage_kill_switch()

    def get_current_regime(self) -> Optional[RegimeSignal]:
        """Get the current regime signal."""
        return self.state.current_regime

    def get_recent_trades(self, limit: int = 50) -> List[Trade]:
        """Get recent trades from portfolio."""
        return self.portfolio.trade_history[-limit:]

    def get_recent_intents(self, limit: int = 50) -> List[FinalTradeIntent]:
        """Get recent trade intents."""
        return self.recent_trade_intents[-limit:]

    def get_agent_fitness(self) -> Dict[str, Dict[str, float]]:
        """Get fitness metrics for all agents."""
        if not self.adaptor:
            return {}
        fitness_map = {}
        for agent in self.agents:
            fitness = self.reward_tracker.memory.get_agent_fitness(agent.name)
            fitness_map[agent.name] = {
                "short_term": fitness.short_term,
                "long_term": fitness.long_term,
                "current_weight": self.adaptor.get_agent_weight(agent.name),
            }
        return fitness_map

    def get_regime_performance(self) -> Dict[str, float]:
        """Get performance metrics by regime."""
        if not self.adaptor:
            return {}
        performance = {}
        from core.regime.types import RegimeType

        for regime in RegimeType:
            fitness = self.reward_tracker.memory.get_regime_fitness(regime)
            weight = self.adaptor.get_regime_weight(regime)
            performance[regime.value] = {"fitness": fitness, "weight": weight}
        return performance

    def get_portfolio_stats(self) -> Dict[str, float]:
        """Get current portfolio statistics."""
        current_price = 0.0
        if self.portfolio.positions:
            pos = list(self.portfolio.positions.values())[0]
            current_price = pos.current_price

        total_value = self.portfolio.get_total_value(current_price)
        return {
            "initial_capital": self.portfolio.initial_capital,
            "current_capital": self.portfolio.current_capital,
            "total_value": total_value,
            "total_return_pct": self.portfolio.get_total_return_pct(),
            "max_drawdown": self.portfolio.get_max_drawdown(),
            "win_rate": self.portfolio.get_win_rate(),
            "sharpe_ratio": self.portfolio.get_sharpe_ratio(),
            "total_trades": len(self.portfolio.trade_history),
            "open_positions": len(self.portfolio.positions),
        }

    def get_risk_status(self) -> Dict[str, any]:
        """Get current risk management status."""
        base_status = {
            "kill_switch_engaged": self.risk_manager.kill_switch_engaged,
            "daily_pnl": self.risk_manager.daily_pnl,
            "loss_streak": self.risk_manager.loss_streak,
            "current_capital": self.risk_manager.current_capital,
            "can_trade": self.risk_manager.can_trade(0.5),  # sample confidence
        }
        if self.advanced_risk:
            base_status["advanced_risk"] = self.advanced_risk.get_risk_metrics()
        return base_status

    def update_state(self, regime: RegimeSignal, intent: FinalTradeIntent) -> None:
        """Update bot state with latest regime and intent."""
        self.state.current_regime = regime
        self.state.last_trade_intent = intent
        self.state.last_update_time = datetime.now()
        # Sync bar_count with live_loop if available (more accurate)
        if self.live_loop and self.live_loop.is_running:
            self.state.bar_count = self.live_loop.bar_count
        else:
            self.state.bar_count += 1

        # Store recent intents
        self.recent_trade_intents.append(intent)
        if len(self.recent_trade_intents) > self.max_recent_intents:
            self.recent_trade_intents.pop(0)

        # Track regime for visualization
        previous_regime = self.regime_history[-1] if self.regime_history else None
        current_regime = regime.regime_type.value
        self.regime_history.append(current_regime)
        if len(self.regime_history) > 1000:  # Keep last 1000
            self.regime_history.pop(0)

        # Log regime flip if occurred
        if self.event_logger and previous_regime and previous_regime != current_regime:
            self.event_logger.log_regime_flip(
                from_regime=previous_regime,
                to_regime=current_regime,
                confidence=regime.confidence,
                bar_count=self.state.bar_count,
            )

        # Track agent fitness evolution
        if self.adaptor:
            for agent in self.agents:
                fitness = self.reward_tracker.memory.get_agent_fitness(agent.name)
                self.agent_fitness_history[agent.name].append(fitness.short_term)
                if len(self.agent_fitness_history[agent.name]) > 500:
                    self.agent_fitness_history[agent.name].pop(0)

            # Track weight evolution
            for agent_name, weight in self.adaptor.agent_weights.items():
                if agent_name not in self.weight_history:
                    self.weight_history[agent_name] = []
                self.weight_history[agent_name].append(weight)
                if len(self.weight_history[agent_name]) > 500:
                    self.weight_history[agent_name].pop(0)

    def get_regime_distribution(self) -> Dict[str, int]:
        """Get distribution of regime types from history."""
        from collections import Counter

        if not self.regime_history:
            return {}
        return dict(Counter(self.regime_history))

    def get_health_status(self) -> Dict[str, any]:
        """Get overall health status of the bot."""
        # Use live_loop bar_count if available (more accurate)
        bar_count = self.state.bar_count
        if self.live_loop and self.live_loop.is_running:
            bar_count = max(bar_count, self.live_loop.bar_count)
            # Also sync state bar_count with live_loop
            if self.live_loop.bar_count > self.state.bar_count:
                self.state.bar_count = self.live_loop.bar_count
        
        return {
            "is_running": self.state.is_running,
            "is_paused": self.state.is_paused,
            "bar_count": bar_count,
            "last_update": self.state.last_update_time.isoformat() if self.state.last_update_time else None,
            "error": self.state.error_message or (self.live_loop.error_message if self.live_loop else None),
            "risk_status": self.get_risk_status(),
            "portfolio_healthy": self.portfolio.get_total_return_pct() > -50.0,  # not down more than 50%
        }

    def start_live_trading(
        self,
        symbols: List[str],
        broker_client: BaseBrokerClient,
        data_feed: BaseDataFeed,
        config: Optional[LiveTradingConfig] = None,
        enable_logging: bool = True,
        asset_profiles: Optional[dict] = None,
    ) -> None:
        """Start live trading with given broker and data feed."""
        if self.mode == "live" and self.live_loop and self.live_loop.is_running:
            raise ValueError("Live trading is already running")

        self.mode = "live"
        self.broker_client = broker_client
        self.data_feed = data_feed
        self.state_store = StateStore()

        # Create live executor
        self.live_executor = LiveTradeExecutor(broker_client)

        # Load asset profiles from config if not provided
        if asset_profiles is None:
            from core.settings_loader import load_settings
            from core.config.asset_profiles import AssetProfileManager
            try:
                settings = load_settings()
                profile_manager = AssetProfileManager()
                if settings.symbols:
                    profile_manager.load_from_config(settings.symbols)
                asset_profiles = {symbol: profile_manager.get_profile(symbol) for symbol in symbols}
            except Exception as e:
                logger.warning(f"Could not load asset profiles: {e}, using defaults")
                asset_profiles = None

        # Create live trading config with fixed investment amount
        live_config = config or LiveTradingConfig(
            symbols=symbols,
            fixed_investment_amount=1000.0,  # $1000 per trade (default, can be overridden by asset profile)
            enable_profit_taking=True,
        )
        
        # Attach asset profiles to config
        if asset_profiles:
            live_config.asset_profiles = asset_profiles
        
        # Update agents for different symbols
        # SPY gets EMA agent, QQQ uses existing agents
        from core.agents.ema_agent import EMAAgent
        updated_agents = list(self.agents)  # Start with existing agents
        
        # If SPY is in symbols, add EMA agent for SPY
        if "SPY" in symbols:
            has_spy_agent = any(agent.symbol == "SPY" for agent in updated_agents)
            if not has_spy_agent:
                spy_ema_agent = EMAAgent(symbol="SPY", config={"ema_period": 9, "min_confidence": 0.5})
                updated_agents.append(spy_ema_agent)
                logger.info("Added EMA agent for SPY (9 EMA momentum strategy)")
        
        # Use updated agents
        agents_to_use = updated_agents

        # Create live trading loop
        self.live_loop = LiveTradingLoop(
            data_feed=data_feed,
            broker_executor=self.live_executor,
            agents=agents_to_use,  # Use updated agents with EMA for SPY
            regime_engine=self.regime_engine,
            controller=self.controller,
            portfolio=self.portfolio,
            risk_manager=self.risk_manager,
            reward_tracker=self.reward_tracker,
            advanced_risk=self.advanced_risk,
            state_store=self.state_store,
            config=live_config,
            on_bar_callback=self.update_state,
        )
        
        # Store agents reference for potential replacement (e.g., challenge mode)
        self._live_agents = agents_to_use

        # Load previous state if available
        saved_state = self.state_store.load_state()
        if saved_state:
            self.live_loop.bar_count = saved_state.get("bar_count", 0)

        # Initialize event logger if enabled
        if enable_logging:
            from pathlib import Path
            self.event_logger = EventLogger(log_file=Path("logs/trading_events.jsonl"))

        # Start the loop
        self.live_loop.start()
        self.state.is_running = True

    def stop_live_trading(self) -> None:
        """Stop live trading."""
        if self.live_loop:
            self.live_loop.stop()
            if self.state_store:
                self.live_loop._save_state()
        
        # Disconnect broker client to free up client ID
        if self.broker_client:
            try:
                self.broker_client.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting broker: {e}")
        
        # Disconnect data feed
        if self.data_feed:
            try:
                self.data_feed.close()
            except Exception as e:
                logger.warning(f"Error closing data feed: {e}")
        
        self.state.is_running = False
        self.mode = "backtest"

    def get_live_status(self) -> Dict[str, any]:
        """Get live trading status."""
        if not self.live_loop:
            return {"mode": "backtest", "is_running": False}

        loop_status = self.live_loop.get_status()
        return {
            "mode": "live",
            **loop_status,
            "symbols": self.live_loop.config.symbols if self.live_loop.config else [],
        }

    def get_live_portfolio(self) -> Dict[str, any]:
        """Get live portfolio snapshot from broker."""
        if not self.broker_client:
            return {}

        account = self.broker_client.get_account()
        positions = self.broker_client.get_positions()

        return {
            "account": {
                "cash": account.cash,
                "equity": account.equity,
                "buying_power": account.buying_power,
                "portfolio_value": account.portfolio_value,
            },
            "positions": [
                {
                    "symbol": pos.symbol,
                    "quantity": pos.quantity,
                    "avg_entry_price": pos.avg_entry_price,
                    "current_price": pos.current_price,
                    "market_value": pos.market_value,
                    "unrealized_pnl": pos.unrealized_pnl,
                }
                for pos in positions
            ],
        }

