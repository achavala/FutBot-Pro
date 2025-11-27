from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Sequence

import pandas as pd

from core.agents.base import BaseAgent
from core.execution.paper import ExecutionConfig, PaperExecutionEngine
from core.features import indicators, stats_features
from core.features.fvg import detect_fvgs
from core.policy.controller import MetaPolicyController
from core.policy.types import FinalTradeIntent
from core.policy_adaptation.adaptor import PolicyAdaptor
from core.portfolio.manager import PortfolioManager
from core.regime.engine import RegimeEngine
from core.regime.types import RegimeSignal
from core.reward.memory import RollingMemoryStore
from core.reward.tracker import RewardTracker
from core.risk.manager import RiskConfig, RiskManager


@dataclass
class BacktestConfig:
    """Configuration for backtest run."""

    initial_capital: float = 100000.0
    symbol: str = "QQQ"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    risk_config: Optional[RiskConfig] = None
    execution_config: Optional[ExecutionConfig] = None
    enable_adaptation: bool = True
    adaptation_frequency: int = 10  # update weights every N bars


@dataclass
class BacktestResults:
    """Results from a backtest run."""

    total_return_pct: float
    max_drawdown: float
    win_rate: float
    sharpe_ratio: float
    total_trades: int
    equity_curve: List[float]
    trade_history: List
    final_capital: float


class BacktestRunner:
    """Orchestrates end-to-end backtesting of the trading system."""

    def __init__(
        self,
        agents: Sequence[BaseAgent],
        regime_engine: RegimeEngine,
        controller: MetaPolicyController,
        config: Optional[BacktestConfig] = None,
    ):
        self.agents = agents
        self.regime_engine = regime_engine
        self.controller = controller
        self.config = config or BacktestConfig()

        # Initialize components
        self.portfolio = PortfolioManager(self.config.initial_capital, self.config.symbol)
        self.risk_manager = RiskManager(self.config.initial_capital, self.config.risk_config)
        self.execution_engine = PaperExecutionEngine(self.config.execution_config)

        # Reward and adaptation
        self.memory_store = RollingMemoryStore()
        self.reward_tracker = RewardTracker(memory_store=self.memory_store)
        self.adaptor = PolicyAdaptor(self.memory_store) if self.config.enable_adaptation else None

        # Update controller with adaptor if available
        if self.adaptor:
            self.controller = MetaPolicyController(adaptor=self.adaptor)

        self.bar_count = 0

    def run(self, data: pd.DataFrame) -> BacktestResults:
        """Run backtest on historical data."""
        if data.empty:
            raise ValueError("DataFrame is empty")

        # Ensure required columns
        required_cols = ["open", "high", "low", "close", "volume"]
        missing = [col for col in required_cols if col not in data.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        # Sort by index (assumed to be datetime)
        data = data.sort_index()

        # Compute features upfront
        data = self._compute_features(data)

        # Process each bar
        for idx, row in data.iterrows():
            self._process_bar(idx, row, data)

        # Finalize results
        return self._finalize_results()

    def _compute_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute all required features for the backtest."""
        # Technical indicators
        df["ema9"] = indicators.ema(df["close"], 9)
        df["sma20"] = indicators.sma(df["close"], 20)
        df["rsi"] = indicators.rsi(df["close"], 14)
        df["atr"] = indicators.atr(df, 14)
        df["adx"] = indicators.adx(df, 14)
        df["vwap"] = indicators.vwap(df)

        # Statistical features
        df["hurst"] = df["close"].rolling(100).apply(lambda x: stats_features.hurst_exponent(x, 2, 20) if len(x) >= 20 else 0.5)
        df["slope"] = df["close"].rolling(30).apply(lambda x: stats_features.rolling_regression(x)[0] if len(x) >= 30 else 0.0)
        df["r_squared"] = df["close"].rolling(30).apply(lambda x: stats_features.rolling_regression(x)[1] if len(x) >= 30 else 0.0)

        # ATR as percentage
        df["atr_pct"] = (df["atr"] / df["close"]) * 100.0

        # VWAP deviation
        df["vwap_deviation"] = ((df["close"] - df["vwap"]) / df["vwap"]) * 100.0

        # Minute displacement
        df["minute_displacement"] = stats_features.minute_displacement(df)

        # IV proxy (simplified - compute on rolling window)
        df["iv_proxy"] = df["atr_pct"] * 1.5  # Simple proxy using ATR%

        return df

    def _process_bar(self, timestamp: datetime, row: pd.Series, full_data: pd.DataFrame) -> None:
        """Process a single bar through the full pipeline."""
        self.bar_count += 1

        # Get recent window for regime detection
        try:
            current_idx = full_data.index.get_loc(timestamp)
        except KeyError:
            return
        window_start = max(0, current_idx - 120)
        window_data = full_data.iloc[window_start : current_idx + 1]

        # Detect FVGs
        fvgs = detect_fvgs(window_data.tail(50))

        # Build market state
        market_state = {
            "close": row["close"],
            "open": row["open"],
            "high": row["high"],
            "low": row["low"],
            "volume": row["volume"],
            "ema9": row.get("ema9", row["close"]),
            "rsi": row.get("rsi", 50.0),
            "atr": row.get("atr", 0.0),
            "vwap": row.get("vwap", row["close"]),
            "vwap_deviation": row.get("vwap_deviation", 0.0),
        }

        # Classify regime
        regime_input = {
            "adx": row.get("adx", 20.0),
            "atr_pct": row.get("atr_pct", 1.0),
            "hurst": row.get("hurst", 0.5),
            "slope": row.get("slope", 0.0),
            "r_squared": row.get("r_squared", 0.0),
            "vwap_deviation": row.get("vwap_deviation", 0.0),
            "iv_proxy": row.get("iv_proxy", 0.0),
            "active_fvgs": fvgs,
            "close": row["close"],
            "bar_index": self.bar_count,
        }

        signal = self.regime_engine.classify_bar(regime_input)

        # Get trade decision from controller
        intent = self.controller.decide(signal, market_state, self.agents)

        # Apply risk management
        if not self.risk_manager.can_trade(intent.confidence):
            intent = FinalTradeIntent(
                position_delta=0.0,
                confidence=0.0,
                primary_agent="NONE",
                contributing_agents=[],
                reason="Risk manager veto",
                is_valid=False,
            )

        # Size position
        if intent.is_valid and intent.position_delta != 0:
            position_size = self.risk_manager.compute_position_size(
                intent.position_delta, row["close"], intent.confidence
            )
            intent.position_delta = position_size / row["close"] if row["close"] > 0 else 0.0

        # Execute
        fill = self.execution_engine.execute_intent(
            intent, self.config.symbol, row["close"], row["high"], row["low"], timestamp
        )

        if fill:
            # Update portfolio
            trade = self.portfolio.apply_position_delta(fill.quantity, fill.fill_price, timestamp)
            if trade:
                # Record trade in risk manager
                self.risk_manager.update_capital(trade.pnl)

        # Update portfolio with current price
        self.portfolio.update_position(self.config.symbol, row["close"])
        self.portfolio.record_equity(row["close"])

        # Compute reward if we have next bar
        try:
            current_idx = full_data.index.get_loc(timestamp)
            next_idx = current_idx + 1
            if next_idx < len(full_data):
            next_row = full_data.iloc[next_idx]
            next_return = (next_row["close"] - row["close"]) / row["close"] if row["close"] > 0 else 0.0

            # Update reward tracker
            contributions = self.reward_tracker.update(intent, next_return, signal)

            # Record structural outcomes for adaptor
            if self.adaptor and signal.active_fvg:
                alignment = "aligned" if (
                    (intent.position_delta > 0 and signal.active_fvg.gap_type == "bullish")
                    or (intent.position_delta < 0 and signal.active_fvg.gap_type == "bearish")
                ) else "conflict"
                success = next_return > 0 if intent.position_delta > 0 else next_return < 0
                self.adaptor.record_structural_outcome(alignment, success)
        except (KeyError, IndexError):
            pass

        # Update adaptive weights periodically
        if self.adaptor and self.bar_count % self.config.adaptation_frequency == 0:
            self.adaptor.update_weights(self.bar_count)

    def _finalize_results(self) -> BacktestResults:
        """Finalize and return backtest results."""
        return BacktestResults(
            total_return_pct=self.portfolio.get_total_return_pct(),
            max_drawdown=self.portfolio.get_max_drawdown(),
            win_rate=self.portfolio.get_win_rate(),
            sharpe_ratio=self.portfolio.get_sharpe_ratio(),
            total_trades=len(self.portfolio.trade_history),
            equity_curve=list(self.portfolio.equity_curve),
            trade_history=self.portfolio.trade_history,
            final_capital=self.portfolio.equity_curve[-1] if self.portfolio.equity_curve else self.config.initial_capital,
        )

