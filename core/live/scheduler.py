from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)

from core.agents.base import BaseAgent
from core.features import indicators, stats_features
from core.features.fvg import detect_fvgs
from core.live.data_feed import BaseDataFeed
from core.live.executor_live import LiveTradeExecutor
from core.live.profit_manager import ProfitManager, ProfitConfig
from core.live.types import Bar
from core.policy.controller import MetaPolicyController
from core.portfolio.manager import PortfolioManager
from core.regime.engine import RegimeEngine
from core.regime.types import RegimeSignal
from core.reward.memory import RollingMemoryStore
from core.reward.tracker import RewardTracker
from core.risk.advanced import AdvancedRiskManager
from core.risk.manager import RiskManager
from services.notifications import NotificationService


@dataclass
class LiveTradingConfig:
    """Configuration for live trading loop."""

    symbols: List[str]
    bar_interval_seconds: int = 60  # 1 minute bars
    adaptation_frequency: int = 10  # Update weights every N bars
    state_save_frequency: int = 50  # Save state every N bars
    enable_advanced_risk: bool = True
    fixed_investment_amount: float = 1000.0  # Fixed $1000 investment per position (default, can be overridden by asset profile)
    enable_profit_taking: bool = True  # Enable automatic profit-taking
    asset_profiles: Optional[dict[str, "AssetProfile"]] = None  # Asset profiles per symbol


class LiveTradingLoop:
    """Main event loop for live trading."""

    def __init__(
        self,
        data_feed: BaseDataFeed,
        broker_executor: LiveTradeExecutor,
        agents: List[BaseAgent],
        regime_engine: RegimeEngine,
        controller: MetaPolicyController,
        portfolio: PortfolioManager,
        risk_manager: RiskManager,
        reward_tracker: RewardTracker,
        advanced_risk: Optional[AdvancedRiskManager] = None,
        state_store=None,
        config: Optional[LiveTradingConfig] = None,
        on_bar_callback: Optional[Callable] = None,
    ):
        self.data_feed = data_feed
        self.executor = broker_executor
        self.agents = agents
        self.regime_engine = regime_engine
        self.controller = controller
        self.portfolio = portfolio
        self.risk_manager = risk_manager
        self.reward_tracker = reward_tracker
        self.advanced_risk = advanced_risk
        self.state_store = state_store
        self.config = config or LiveTradingConfig(symbols=["QQQ"])
        self.on_bar_callback = on_bar_callback

        self.is_running = False
        self.is_paused = False
        self.thread: Optional[threading.Thread] = None
        self.bar_count = 0
        self.last_bar_time: Optional[datetime] = None
        self.error_message: Optional[str] = None

        # Feature buffers
        self.bar_history: dict[str, List[Bar]] = {symbol: [] for symbol in self.config.symbols}
        
        # Asset profiles (if provided)
        self.asset_profiles: Optional[dict[str, "AssetProfile"]] = getattr(config, 'asset_profiles', None) if config else None
        
        # Profit manager for automatic profit-taking (with asset profiles)
        if self.config.enable_profit_taking:
            self.profit_manager = ProfitManager(asset_profiles=self.asset_profiles)
        else:
            self.profit_manager = None
        
        # Notification service for email and SMS
        try:
            self.notification_service = NotificationService()
            logger.info("Notification service initialized")
        except Exception as e:
            logger.warning(f"Notification service not available: {e}")
            self.notification_service = None

    def start(self) -> None:
        """Start the live trading loop in a background thread."""
        if self.is_running:
            raise ValueError("Live trading loop is already running")

        if not self.data_feed.connected:
            self.data_feed.connect()
            # Preload bars - request 100 bars to ensure we get at least 50+ bars
            # This speeds up startup by loading historical data immediately
            self.data_feed.subscribe(self.config.symbols, preload_bars=100)  # Preload 100 bars for faster startup
            
            # Load preloaded bars into history (wait for preload to complete)
            # Increased wait time but handle partial loads gracefully
            import time
            time.sleep(8)  # Give preload more time to complete (cache + IBKR)
            
            for symbol in self.config.symbols:
                if hasattr(self.data_feed, 'bar_buffers') and symbol in self.data_feed.bar_buffers:
                    # Copy all bars from buffer
                    preloaded = list(self.data_feed.bar_buffers[symbol])
                    for bar in preloaded:
                        # Check if bar already exists (by timestamp)
                        if not any(b.timestamp == bar.timestamp for b in self.bar_history[symbol]):
                            self.bar_history[symbol].append(bar)
                    
                    loaded_count = len(self.bar_history[symbol])
                    logger.info(f"Loaded {loaded_count} bars for {symbol} (preloaded: {len(preloaded)})")
                    
                    # Update bar_count to reflect preloaded bars
                    if loaded_count > 0:
                        self.bar_count = max(self.bar_count, loaded_count)
                    
                    # Warn if we have fewer bars than desired, but continue anyway
                    if loaded_count < 50:
                        logger.warning(
                            f"Only {loaded_count} bars loaded for {symbol} (target: 60). "
                            f"Bot will accumulate bars naturally over time. Trading will start once 50+ bars are available."
                        )

        self.is_running = True
        self.is_paused = False
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        """Stop the live trading loop."""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5.0)

    def pause(self) -> None:
        """Pause the loop (keeps connection alive)."""
        self.is_paused = True

    def resume(self) -> None:
        """Resume the loop."""
        self.is_paused = False

    def _run_loop(self) -> None:
        """Main event loop (runs in background thread)."""
        while self.is_running:
            try:
                if self.is_paused:
                    time.sleep(1.0)
                    continue

                # Process each symbol
                for symbol in self.config.symbols:
                    bar = self.data_feed.get_next_bar(symbol, timeout=1.0)
                    if bar:
                        self._process_bar(symbol, bar)

                # Sleep until next bar interval
                time.sleep(self.config.bar_interval_seconds)

            except Exception as e:
                error_str = str(e)
                # Don't store VWAP/DatetimeIndex errors (handled with fallback) or KeyError: 0 (handled)
                if "VWAP" not in error_str and "DatetimeIndex" not in error_str and error_str != "0":
                    self.error_message = error_str
                    # Log detailed error for debugging
                    import traceback
                    logger.error(f"Error in live trading loop: {e}")
                    logger.error(f"Traceback: {traceback.format_exc()}")
                else:
                    # Clear error message for handled errors
                    self.error_message = None
                # Continue running but log error
                time.sleep(5.0)

    def _process_bar(self, symbol: str, bar: Bar) -> None:
        """Process a single bar through the full pipeline."""
        self.bar_count += 1
        self.last_bar_time = bar.timestamp

        # Add to history (if not already present from preload)
        if not self.bar_history[symbol] or self.bar_history[symbol][-1].timestamp != bar.timestamp:
            self.bar_history[symbol].append(bar)
            if len(self.bar_history[symbol]) > 500:
                self.bar_history[symbol].pop(0)

        # Convert bars to DataFrame for feature computation
        import pandas as pd

        bars_df = pd.DataFrame(
            [
                {
                    "timestamp": b.timestamp,
                    "open": b.open,
                    "high": b.high,
                    "low": b.low,
                    "close": b.close,
                    "volume": b.volume,
                }
                for b in self.bar_history[symbol]
            ]
        )
        
        # Set timestamp as DatetimeIndex (required for VWAP calculation)
        if not bars_df.empty and "timestamp" in bars_df.columns:
            bars_df["timestamp"] = pd.to_datetime(bars_df["timestamp"])
            bars_df = bars_df.set_index("timestamp")
            # Ensure index is DatetimeIndex (double-check)
            if not isinstance(bars_df.index, pd.DatetimeIndex):
                bars_df.index = pd.to_datetime(bars_df.index)
        elif not bars_df.empty and not isinstance(bars_df.index, pd.DatetimeIndex):
            # If timestamp is already the index but not DatetimeIndex, convert it
            bars_df.index = pd.to_datetime(bars_df.index)

        # Always call callback to update BotManager state, even if we don't have enough bars yet
        # If we don't have enough bars, still update regime with "waiting" state
        # Lowered threshold to 30 bars to allow earlier trading
        if len(bars_df) < 30:  # Need enough history for features (lowered from 50)
            if self.on_bar_callback:
                # Create a "waiting" regime signal to show progress
                from core.regime.types import RegimeSignal, RegimeType, TrendDirection, VolatilityLevel, Bias
                waiting_signal = RegimeSignal(
                    timestamp=bar.timestamp,
                    trend_direction=TrendDirection.SIDEWAYS,
                    volatility_level=VolatilityLevel.LOW,
                    regime_type=RegimeType.COMPRESSION,
                    bias=Bias.NEUTRAL,
                    confidence=0.0,
                    active_fvg=None,
                    metrics={"bar_count": len(bars_df), "required_bars": 50},
                    is_valid=False,
                )
                # Create a no-op intent
                from core.policy.types import FinalTradeIntent
                no_op_intent = FinalTradeIntent(
                    position_delta=0.0,
                    confidence=0.0,
                    primary_agent="NONE",
                    contributing_agents=[],
                    reason=f"Waiting for more bars ({len(bars_df)}/50)",
                    is_valid=False,
                )
                # IMPORTANT: Call callback to update BotManager state with current bar count
                self.on_bar_callback(waiting_signal, no_op_intent)
            return

        # Compute features (ensure DatetimeIndex is preserved)
        # Double-check DatetimeIndex before computing features
        if not isinstance(bars_df.index, pd.DatetimeIndex) and not bars_df.empty:
            logger.warning(f"DatetimeIndex lost before _compute_features! Index type: {type(bars_df.index)}")
            if "timestamp" in bars_df.columns:
                bars_df = bars_df.set_index("timestamp")
                bars_df.index = pd.to_datetime(bars_df.index)
        
        bars_df = self._compute_features(bars_df)

        # Get latest row
        latest = bars_df.iloc[-1]

        # Detect FVGs
        fvgs = detect_fvgs(bars_df.tail(50))

        # Build market state
        market_state = {
            "close": latest["close"],
            "open": latest["open"],
            "high": latest["high"],
            "low": latest["low"],
            "volume": latest["volume"],
            "ema9": latest.get("ema9", latest["close"]),
            "rsi": latest.get("rsi", 50.0),
            "atr": latest.get("atr", 0.0),
            "vwap": latest.get("vwap", latest["close"]),
            "vwap_deviation": latest.get("vwap_deviation", 0.0),
        }

        # Get asset type for this symbol (if available from asset profiles)
        asset_type = "equity"  # Default
        if hasattr(self, 'asset_profiles') and symbol in self.asset_profiles:
            asset_type = self.asset_profiles[symbol].asset_type.value
        
        # Classify regime
        regime_input = {
            "adx": latest.get("adx", 20.0),
            "atr_pct": latest.get("atr_pct", 1.0),
            "hurst": latest.get("hurst", 0.5),
            "slope": latest.get("slope", 0.0),
            "r_squared": latest.get("r_squared", 0.0),
            "vwap_deviation": latest.get("vwap_deviation", 0.0),
            "iv_proxy": latest.get("iv_proxy", 0.0),
            "active_fvgs": fvgs,
            "close": latest["close"],
            "bar_index": self.bar_count,
            "asset_type": asset_type,  # Include asset type for asset-aware regime classification
        }

        signal = self.regime_engine.classify_bar(regime_input)
        
        # Log regime classification for debugging
        if self.bar_count % 10 == 0:  # Log every 10 bars
            logger.info(
                f"Regime: {signal.regime_type.value}, "
                f"Confidence: {signal.confidence:.2f}, "
                f"Valid: {signal.is_valid}, "
                f"Bias: {signal.bias.value}, "
                f"ADX: {latest.get('adx', 0):.2f}, "
                f"Hurst: {latest.get('hurst', 0.5):.2f}, "
                f"Slope: {latest.get('slope', 0.0):.4f}, "
                f"R²: {latest.get('r_squared', 0.0):.2f}"
            )
        
        # If regime is invalid but we have enough bars, try to force valid
        # This helps when features have NaN values that are being handled
        if not signal.is_valid and len(bars_df) >= 30:
            # Re-check with filled NaN values
            adx_val = latest.get("adx", 20.0)
            slope_val = latest.get("slope", 0.0)
            r2_val = latest.get("r_squared", 0.0)
            hurst_val = latest.get("hurst", 0.5)
            atr_val = latest.get("atr_pct", 1.0)
            
            # If all values are valid numbers, mark as valid
            import numpy as np
            if not np.isnan([adx_val, slope_val, r2_val, hurst_val, atr_val]).any():
                # Create a new signal with is_valid=True
                from core.regime.types import RegimeSignal
                signal = RegimeSignal(
                    timestamp=signal.timestamp,
                    trend_direction=signal.trend_direction,
                    volatility_level=signal.volatility_level,
                    regime_type=signal.regime_type,
                    bias=signal.bias,
                    confidence=max(signal.confidence, 0.3),  # Ensure minimum confidence
                    active_fvg=signal.active_fvg,
                    metrics=signal.metrics,
                    is_valid=True,
                )
                logger.info(f"Force-validated regime signal (confidence: {signal.confidence:.2f})")

        # Before calling controller, update options agents with base agent signals for alignment
        # This allows options agents to check if base agents align
        options_agents = [a for a in self.agents if hasattr(a, 'options_data_feed')]
        base_agents = [a for a in self.agents if not hasattr(a, 'options_data_feed')]
        
        if options_agents and base_agents:
            # Collect intents from base agents first (for options agent alignment)
            base_intents = []
            for agent in base_agents:
                try:
                    agent_intents = agent.evaluate(signal, market_state)
                    base_intents.extend(agent_intents)
                except Exception as e:
                    logger.warning(f"Base agent {agent.name} evaluation failed: {e}")
            
            # Update options agents with signals from base agents
            for options_agent in options_agents:
                # Find intents from each base agent type
                trend_intent = next((i for i in base_intents if 'trend' in i.agent_name.lower()), None)
                mr_intent = next((i for i in base_intents if 'mean' in i.agent_name.lower() or 'reversion' in i.agent_name.lower()), None)
                vol_intent = next((i for i in base_intents if 'volatility' in i.agent_name.lower() or 'vol' in i.agent_name.lower()), None)
                
                # Update options agent signals
                if hasattr(options_agent, 'trend_agent_signal'):
                    options_agent.trend_agent_signal = trend_intent
                if hasattr(options_agent, 'mean_reversion_agent_signal'):
                    options_agent.mean_reversion_agent_signal = mr_intent
                if hasattr(options_agent, 'volatility_agent_signal'):
                    options_agent.volatility_agent_signal = vol_intent
        
        # Get trade decision (includes options agent now)
        intent = self.controller.decide(signal, market_state, self.agents)

        # Get current position from broker
        positions = self.executor.broker_client.get_positions(symbol)
        current_position = positions[0].quantity if positions else 0.0
        
        # Check profit-taking for existing positions
        if self.profit_manager and current_position != 0:
            should_close, reason = self.profit_manager.should_take_profit(
                symbol, latest["close"], self.bar_count, signal
            )
            if should_close:
                logger.info(f"Taking profit for {symbol}: {reason}")
                # Close position
                result = self.executor.close_position(symbol, current_position)
                if result.success:
                    # Update portfolio
                    if symbol in self.portfolio.positions:
                        trade = self.portfolio.close_position(
                            symbol, latest["close"], bar.timestamp, reason, "profit_manager"
                        )
                        if trade:
                            logger.info(f"Closed position: {symbol}, PnL: ${trade.pnl:.2f} ({trade.pnl_pct:.2f}%)")
                            
                            # Record trade in challenge risk manager
                            if hasattr(self, 'challenge_risk_manager') and self.challenge_risk_manager:
                                is_win = trade.pnl > 0
                                self.challenge_risk_manager.record_trade(is_win)
                            
                            # Send notification for position close
                            if self.notification_service:
                                try:
                                    self.notification_service.send_trade_notification(
                                        symbol=symbol,
                                        side="SELL",
                                        quantity=abs(trade.quantity),
                                        price=trade.exit_price,
                                        order_id=result.order.order_id if result.order else None,
                                        pnl=trade.pnl,
                                        pnl_pct=trade.pnl_pct,
                                    )
                                except Exception as e:
                                    logger.error(f"Failed to send close position notification: {e}")
                    # Stop tracking
                    self.profit_manager.remove_position(symbol)
                    # Update position
                    current_position = 0.0

        # Advanced risk check
        if self.advanced_risk:
            can_trade, risk_reason = self.advanced_risk.can_trade_advanced(
                intent.confidence, signal.regime_type, signal.volatility_level, self.bar_count
            )
            if not can_trade:
                intent = intent.__class__(
                    position_delta=0.0,
                    confidence=0.0,
                    primary_agent="NONE",
                    contributing_agents=[],
                    reason=f"Risk veto: {risk_reason}",
                    is_valid=False,
                )

        # Execute if valid
        if intent.is_valid and intent.position_delta != 0:
            # Get investment amount from asset profile or config
            if self.asset_profiles and symbol in self.asset_profiles:
                profile = self.asset_profiles[symbol]
                base_investment = profile.fixed_investment_amount or self.config.fixed_investment_amount
            else:
                base_investment = self.config.fixed_investment_amount
            
            # Calculate target quantity based on $1000 investment
            target_quantity = base_investment / latest["close"] if latest["close"] > 0 else 0.0
            
            # Apply direction (positive = buy, negative = sell)
            if intent.position_delta > 0:
                # Want to go long - buy shares
                target_quantity = abs(target_quantity)
            else:
                # Want to go short - sell shares
                target_quantity = -abs(target_quantity)
            
            # Calculate position delta needed
            position_delta = target_quantity - current_position
            
            # Compute risk-constrained size
            risk_constraints = {}
            if self.advanced_risk:
                # Use $1000 as base size, let risk manager adjust
                size, _ = self.advanced_risk.compute_advanced_position_size(
                    base_investment,
                    latest["close"],
                    intent.confidence,
                    signal.regime_type,
                    signal.volatility_level,
                    self.bar_count,
                )
                # Convert dollar size to quantity
                max_quantity = size / latest["close"] if latest["close"] > 0 else 0.0
                # Apply direction
                if intent.position_delta > 0:
                    max_quantity = abs(max_quantity)
                else:
                    max_quantity = -abs(max_quantity)
                
                # Cap position delta by risk constraints
                if abs(position_delta) > abs(max_quantity):
                    position_delta = max_quantity if position_delta > 0 else -abs(max_quantity)
                
                risk_constraints["max_size"] = abs(max_quantity)
            
            # Only execute if position delta is significant
            if abs(position_delta) > 0.01:  # At least 0.01 shares
                # Create modified intent with calculated position delta
                modified_intent = intent.__class__(
                    position_delta=position_delta / latest["close"] if latest["close"] > 0 else 0.0,
                    confidence=intent.confidence,
                    primary_agent=intent.primary_agent,
                    contributing_agents=intent.contributing_agents,
                    reason=f"{intent.reason} (${base_investment:.0f} investment)",
                    is_valid=True,
                )
                
                result = self.executor.apply_intent(modified_intent, symbol, latest["close"], current_position, risk_constraints)
                if result.success and result.order:
                    # Determine if this is a buy or sell
                    is_buy = result.position_delta_applied > 0
                    side = "BUY" if is_buy else "SELL"
                    quantity = abs(result.position_delta_applied)
                    price = latest["close"]
                    
                    # Send notification
                    if self.notification_service:
                        try:
                            self.notification_service.send_trade_notification(
                                symbol=symbol,
                                side=side,
                                quantity=quantity,
                                price=price,
                                order_id=result.order.order_id if result.order else None,
                            )
                        except Exception as e:
                            logger.error(f"Failed to send notification: {e}")
                    
                    # Update portfolio
                    trade = self.portfolio.apply_position_delta(result.position_delta_applied, latest["close"], bar.timestamp)
                    
                    # If position was closed (trade returned), send sell notification with PnL
                    if trade and not is_buy:
                        if self.notification_service:
                            try:
                                self.notification_service.send_trade_notification(
                                    symbol=symbol,
                                    side="SELL",
                                    quantity=abs(trade.quantity),
                                    price=trade.exit_price,
                                    order_id=result.order.order_id if result.order else None,
                                    pnl=trade.pnl,
                                    pnl_pct=trade.pnl_pct,
                                )
                            except Exception as e:
                                logger.error(f"Failed to send sell notification: {e}")
                    
                    # Start tracking position for profit-taking
                    if self.profit_manager:
                        new_position = current_position + result.position_delta_applied
                        if abs(new_position) > 0.01:  # Only track if we have a position
                            # Get entry price from portfolio
                            if symbol in self.portfolio.positions:
                                entry_price = self.portfolio.positions[symbol].entry_price
                            else:
                                entry_price = latest["close"]
                            
                            self.profit_manager.track_position(
                                symbol=symbol,
                                entry_price=entry_price,
                                quantity=new_position,
                                entry_time=bar.timestamp,
                                entry_bar=self.bar_count,
                            )

        # Update portfolio equity
        self.portfolio.update_position(symbol, latest["close"])
        self.portfolio.record_equity(latest["close"])
        
        # Update profit manager
        if self.profit_manager:
            self.profit_manager.update_position(symbol, latest["close"], self.bar_count)

        # Update advanced risk equity
        if self.advanced_risk:
            total_value = self.portfolio.get_total_value(latest["close"])
            self.advanced_risk.update_equity(total_value)
        
        # Update challenge risk manager if active
        if hasattr(self, 'challenge_risk_manager') and self.challenge_risk_manager:
            current_equity = self.portfolio.get_total_equity()
            self.challenge_risk_manager.update_capital(current_equity)

        # Callback for BotManager
        if self.on_bar_callback:
            self.on_bar_callback(signal, intent)

        # Update weights periodically
        if self.bar_count % self.config.adaptation_frequency == 0:
            # TODO: Update adaptor weights
            pass

        # Save state periodically
        if self.state_store and self.bar_count % self.config.state_save_frequency == 0:
            self._save_state()

    def _compute_features(self, df) -> pd.DataFrame:
        """Compute features for bars DataFrame."""
        import pandas as pd

        # Ensure DataFrame has DatetimeIndex (required for VWAP)
        # This should already be set in _process_bar, but double-check here
        if df.empty:
            logger.warning("Empty DataFrame passed to _compute_features")
            return df
            
        if not isinstance(df.index, pd.DatetimeIndex):
            # Try to set timestamp as index if it exists as a column
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df = df.set_index("timestamp")
            # If timestamp is already the index but not DatetimeIndex, convert it
            elif df.index.name == "timestamp" or isinstance(df.index, pd.RangeIndex):
                # Try to convert index to DatetimeIndex
                try:
                    df.index = pd.to_datetime(df.index)
                except:
                    # If that fails, check if we have a timestamp column
                    if "timestamp" in df.columns:
                        df = df.set_index("timestamp")
                        df.index = pd.to_datetime(df.index)
            
            # Final check
            if not isinstance(df.index, pd.DatetimeIndex):
                logger.error(f"Failed to set DatetimeIndex. Index type: {type(df.index)}, columns: {df.columns.tolist()}")
                raise ValueError(f"Cannot compute VWAP: DataFrame index is {type(df.index)}, not DatetimeIndex")

        # Technical indicators
        df["ema9"] = indicators.ema(df["close"], 9)
        df["sma20"] = indicators.sma(df["close"], 20)
        df["rsi"] = indicators.rsi(df["close"], 14)
        df["atr"] = indicators.atr(df, 14)
        df["adx"] = indicators.adx(df, 14)
        
        # VWAP requires DatetimeIndex - try to compute, fallback if needed
        try:
            # Ensure DatetimeIndex before calling vwap
            if not isinstance(df.index, pd.DatetimeIndex):
                if "timestamp" in df.columns:
                    df = df.set_index("timestamp")
                df.index = pd.to_datetime(df.index)
            
            # Try to compute VWAP with session boundaries
            df["vwap"] = indicators.vwap(df)
        except (ValueError, TypeError, KeyError) as e:
            # If VWAP fails (e.g., no DatetimeIndex), use simple cumulative VWAP
            logger.warning(f"VWAP calculation failed ({e}), using fallback cumulative VWAP")
            if df.empty or "close" not in df.columns or "volume" not in df.columns:
                df["vwap"] = pd.Series(dtype=float, index=df.index)
            else:
                # Use simple cumulative VWAP without session boundaries
                df["vwap"] = (df["close"] * df["volume"]).cumsum() / df["volume"].cumsum()

        # Statistical features (with better NaN handling)
        df["hurst"] = df["close"].rolling(100, min_periods=20).apply(
            lambda x: stats_features.hurst_exponent(x, 2, 20) if len(x) >= 20 else 0.5
        ).fillna(0.5)  # Default to 0.5 (random walk) if not enough data
        df["slope"] = df["close"].rolling(30, min_periods=10).apply(
            lambda x: stats_features.rolling_regression(x)[0] if len(x) >= 10 else 0.0
        ).fillna(0.0)
        df["r_squared"] = df["close"].rolling(30, min_periods=10).apply(
            lambda x: stats_features.rolling_regression(x)[1] if len(x) >= 10 else 0.0
        ).fillna(0.0)

        df["atr_pct"] = (df["atr"] / df["close"]) * 100.0
        df["vwap_deviation"] = ((df["close"] - df["vwap"]) / df["vwap"]) * 100.0
        df["minute_displacement"] = stats_features.minute_displacement(df)
        df["iv_proxy"] = df["atr_pct"] * 1.5  # Simple proxy

        return df

    def _save_state(self) -> None:
        """Save current state to state store."""
        if not self.state_store:
            return

        state = {
            "bar_count": self.bar_count,
            "last_bar_time": self.last_bar_time.isoformat() if self.last_bar_time else None,
            "portfolio_capital": self.portfolio.current_capital,
        }
        self.state_store.update_state(state)

    def get_status(self) -> dict:
        """Get current loop status."""
        return {
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "bar_count": self.bar_count,
            "last_bar_time": self.last_bar_time.isoformat() if self.last_bar_time else None,
            "error": self.error_message,
        }

