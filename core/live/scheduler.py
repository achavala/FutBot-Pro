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
from core.live.executor_options import SyntheticOptionsExecutor
from core.live.profit_manager import ProfitManager, ProfitConfig
from core.live.types import Bar
from core.policy.controller import MetaPolicyController
from core.portfolio.manager import PortfolioManager
from core.portfolio.options_manager import OptionsPortfolioManager
from core.regime.engine import RegimeEngine
from core.regime.types import RegimeSignal
from core.regime.microstructure import MarketMicrostructure
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
    offline_mode: bool = False  # Explicit offline/cached mode flag
    replay_speed_multiplier: float = 600.0  # Replay speed: 1.0 = real-time, 600.0 = 600x speed (0.1s per bar)
    testing_mode: bool = False  # Force trading mode - allows trading with minimal bars
    minimum_bars_required: int = 10  # Minimum bars for analysis (10 for relaxed, 1 for testing_mode)


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
        self.stop_reason: Optional[str] = None  # Reason for stopping (e.g., "end_of_data", "user_stop", "error")
        self.start_time: Optional[datetime] = None  # Track when loop started
        self.bars_per_symbol: dict[str, int] = {symbol: 0 for symbol in self.config.symbols}  # Track bars per symbol

        # Feature buffers
        self.bar_history: dict[str, List[Bar]] = {symbol: [] for symbol in self.config.symbols}
        
        # Asset profiles (if provided)
        self.asset_profiles: Optional[dict[str, "AssetProfile"]] = getattr(config, 'asset_profiles', None) if config else None
        
        # Profit manager for automatic profit-taking (with asset profiles)
        if self.config.enable_profit_taking:
            self.profit_manager = ProfitManager(asset_profiles=self.asset_profiles)
        else:
            self.profit_manager = None
        
        # Options portfolio and executor
        self.options_portfolio = OptionsPortfolioManager()
        # Get options data feed from any options agent (if available)
        options_data_feed = None
        for agent in self.agents:
            if hasattr(agent, 'options_data_feed') and agent.options_data_feed:
                options_data_feed = agent.options_data_feed
                logger.info(f"✅ [LiveLoop] Found options data feed from {agent.name}")
                break
        self.options_data_feed = options_data_feed  # Store for GEX calculation in _process_bar
        
        # Create options broker client for real Alpaca orders (if executor is Alpaca)
        options_broker_client = None
        if hasattr(self.executor, 'broker_client'):
            broker = self.executor.broker_client
            # Check if it's an Alpaca broker (supports options)
            if hasattr(broker, 'trading_client') and hasattr(broker, 'is_paper'):
                try:
                    from core.live.options_broker_client import OptionsBrokerClient
                    # Create options broker client using same credentials
                    options_broker_client = OptionsBrokerClient(
                        api_key=broker.api_key,
                        api_secret=broker.api_secret,
                        base_url=broker.base_url,
                    )
                    logger.info(f"✅ [LiveLoop] Options broker client initialized (paper={broker.is_paper})")
                except Exception as e:
                    logger.warning(f"⚠️ [LiveLoop] Could not create options broker client: {e}")
        
        self.options_executor = SyntheticOptionsExecutor(
            self.options_portfolio, 
            options_data_feed=options_data_feed,
            options_broker_client=options_broker_client,  # Real Alpaca orders enabled
        )
        
        # Multi-leg profit manager for straddles/strangles
        from core.live.multi_leg_profit_manager import MultiLegProfitManager
        self.multi_leg_profit_manager = MultiLegProfitManager(
            options_data_feed=options_data_feed,
        )
        
        # Pass options_broker_client to agents that need it (for Alpaca detection)
        # This allows agents to detect Alpaca paper mode and adjust behavior
        # (e.g., ThetaHarvesterAgent disables real straddle selling in Alpaca paper)
        for agent in self.agents:
            if hasattr(agent, 'options_broker_client'):
                agent.options_broker_client = options_broker_client
                # Trigger Alpaca paper mode detection if needed
                if hasattr(agent, '__init__'):
                    # Re-check Alpaca paper mode after broker client is set
                    if options_broker_client and hasattr(options_broker_client, 'is_paper'):
                        if options_broker_client.is_paper and hasattr(agent, 'alpaca_paper_mode'):
                            agent.alpaca_paper_mode = True
                            logger.info(f"✅ [LiveLoop] {agent.name} detected Alpaca paper mode - straddle selling will use SIM mode")
        
        # Market Microstructure (singleton for GEX data)
        self.microstructure = MarketMicrostructure()
        
        # Notification service for email and SMS
        try:
            self.notification_service = NotificationService()
            logger.info("Notification service initialized")
        except Exception as e:
            logger.warning(f"Notification service not available: {e}")
            self.notification_service = None

    def start(self) -> None:
        """Start the live trading loop in a background thread."""
        logger.info(f"🔵 [LiveLoop] Starting live trading loop...")
        if self.is_running:
            raise ValueError("Live trading loop is already running")
        
        # Clear any previous error state
        self.error_message = None
        self.stop_reason = None

        logger.info(f"🔵 [LiveLoop] Data feed connected: {self.data_feed.connected}")
        if not self.data_feed.connected:
            logger.info(f"🔵 [LiveLoop] Connecting data feed...")
            self.data_feed.connect()
            logger.info(f"✅ [LiveLoop] Data feed connected successfully")
            # Preload bars - request 100 bars to ensure we get at least 50+ bars
            # This speeds up startup by loading historical data immediately
            logger.info(f"🔵 [LiveLoop] Subscribing to symbols {self.config.symbols} with preload_bars=100...")
            subscribe_result = self.data_feed.subscribe(self.config.symbols, preload_bars=100)  # Preload 100 bars for faster startup
            logger.info(f"✅ [LiveLoop] Subscribe result: {subscribe_result}")
            
            # Load preloaded bars into history (wait for preload to complete)
            # Increased wait time but handle partial loads gracefully
            import time
            time.sleep(8)  # Give preload more time to complete (cache + IBKR)
            
            # CRITICAL FIX: Process preloaded bars through _process_bar() to trigger trades
            # Previously, preloaded bars were only added to bar_history but not processed
            # This caused bars_per_symbol to be stuck at preload count and no trades to execute
            for symbol in self.config.symbols:
                if hasattr(self.data_feed, 'bar_buffers') and symbol in self.data_feed.bar_buffers:
                    # Get preloaded bars from buffer
                    preloaded = list(self.data_feed.bar_buffers[symbol])
                    logger.info(f"🔵 [LiveLoop] Processing {len(preloaded)} preloaded bars for {symbol} through trading pipeline...")
                    
                    # Process each preloaded bar through the full trading pipeline
                    processed_count = 0
                    for bar in preloaded:
                        # Check if bar already exists (by timestamp) to avoid duplicates
                        if not any(b.timestamp == bar.timestamp for b in self.bar_history[symbol]):
                            # CRITICAL: Process bar through _process_bar() to trigger trading logic
                            self._process_bar(symbol, bar)
                            processed_count += 1
                            # Ensure symbol case matches exactly (SPY not spy)
                            symbol_key = symbol.upper() if isinstance(symbol, str) else symbol
                            # bars_per_symbol is already incremented in _process_bar() via the loop logic
                            logger.debug(f"✅ [LiveLoop] Processed preloaded bar #{processed_count} for {symbol_key}: {bar.timestamp}")
                    
                    # CRITICAL: Update current_indices to skip past preloaded bars
                    # This prevents the loop from re-processing the same bars
                    if hasattr(self.data_feed, 'current_indices') and hasattr(self.data_feed, 'cached_data'):
                        if symbol in self.data_feed.cached_data:
                            # Skip past the preloaded bars
                            preload_count = len(preloaded)
                            current_idx = self.data_feed.current_indices.get(symbol, 0)
                            # Only update if we haven't already advanced past preload
                            if current_idx < preload_count:
                                self.data_feed.current_indices[symbol] = preload_count
                                logger.info(f"✅ [LiveLoop] Updated current_indices['{symbol}'] to {preload_count} to skip preloaded bars")
                    
                    symbol_key = symbol.upper() if isinstance(symbol, str) else symbol
                    logger.info(f"✅ [LiveLoop] Processed {processed_count} preloaded bars for {symbol}, bars_per_symbol['{symbol_key}'] = {self.bars_per_symbol.get(symbol_key, 0)}")
                    logger.info(f"✅ [LiveLoop] Current state: bar_count={self.bar_count}, bars_per_symbol={self.bars_per_symbol}")
                    
                    # Warn if we have fewer bars than desired, but continue anyway
                    if processed_count < 50:
                        logger.warning(
                            f"Only {processed_count} bars processed for {symbol} (target: 60). "
                            f"Bot will accumulate bars naturally over time. Trading will start once 50+ bars are available."
                        )

        self.is_running = True
        self.is_paused = False
        logger.info(f"🔵 [LiveLoop] Creating background thread for _run_loop...")
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info(f"✅ [LiveLoop] Background thread started - loop is now running")

    def stop(self) -> None:
        """Stop the live trading loop."""
        if self.is_running:
            self.stop_reason = "user_stop"
            # Only log summary if we have processed some bars
            if hasattr(self.config, 'offline_mode') and self.config.offline_mode and self.bar_count > 0:
                try:
                    self._log_simulation_summary()
                except Exception as e:
                    logger.warning(f"Could not log simulation summary: {e}")
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5.0)
    
    def _log_simulation_summary(self) -> None:
        """Log summary statistics when simulation completes."""
        if not self.start_time:
            return
        
        from datetime import datetime, timezone
        duration = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        
        logger.info("=" * 60)
        logger.info("📊 SIMULATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
        logger.info(f"Total bars processed: {self.bar_count}")
        logger.info(f"Bars per symbol:")
        for symbol, count in self.bars_per_symbol.items():
            logger.info(f"  {symbol}: {count} bars")
        if duration > 0:
            bars_per_second = self.bar_count / duration
            logger.info(f"Processing speed: {bars_per_second:.1f} bars/second")
        # Get final portfolio value from equity curve or calculate from current capital
        if self.portfolio.equity_curve:
            final_value = self.portfolio.equity_curve[-1]
        else:
            # Fallback: use current capital if no equity curve
            final_value = self.portfolio.current_capital
        logger.info(f"Final portfolio value: ${final_value:,.2f}")
        logger.info(f"Total trades: {len(self.portfolio.trade_history) if hasattr(self.portfolio, 'trade_history') else 0}")
        logger.info("=" * 60)

    def pause(self) -> None:
        """Pause the loop (keeps connection alive)."""
        self.is_paused = True

    def resume(self) -> None:
        """Resume the loop."""
        self.is_paused = False

    def _run_loop(self) -> None:
        """Main event loop (runs in background thread)."""
        from datetime import datetime, timezone
        self.start_time = datetime.now(timezone.utc)
        logger.info(f"🔵 [LiveLoop] _run_loop() STARTED - thread is running!")
        
        # Use explicit offline_mode from config, or detect via cache_path
        is_offline_mode = self.config.offline_mode or hasattr(self.data_feed, 'cache_path')
        
        # Initialize last_bar_time to start_date if available (for accurate date display)
        if is_offline_mode and hasattr(self.data_feed, 'start_date') and self.data_feed.start_date:
            # Set last_bar_time to start_date so UI shows correct date immediately
            self.last_bar_time = self.data_feed.start_date
            # Ensure timezone-aware
            if self.last_bar_time.tzinfo is None:
                self.last_bar_time = self.last_bar_time.replace(tzinfo=timezone.utc)
            logger.info(f"🔵 [LiveLoop] Initialized last_bar_time to start_date: {self.last_bar_time}")
        
        # Calculate sleep interval based on replay speed
        if is_offline_mode:
            # In offline mode, use replay speed multiplier
            base_interval = self.config.bar_interval_seconds
            # Fix division by zero: ensure replay_speed_multiplier is at least 0.1
            replay_speed = max(self.config.replay_speed_multiplier, 0.1) if self.config.replay_speed_multiplier else 600.0
            sleep_interval = base_interval / replay_speed
            logger.info(f"🔵 [LiveLoop] OFFLINE MODE ENABLED")
            logger.info(f"🔵 [LiveLoop] Replay speed: {replay_speed}x ({sleep_interval:.3f}s per bar)")
            logger.info(f"🔵 [LiveLoop] Processing up to 10 bars per iteration")
            if hasattr(self.data_feed, 'start_date') and self.data_feed.start_date:
                logger.info(f"🔵 [LiveLoop] Beginning replay at {self.data_feed.start_date}")
        else:
            sleep_interval = self.config.bar_interval_seconds
            logger.info(f"🔵 [LiveLoop] Mode = LIVE (realtime) - Interval: {sleep_interval}s per bar")
        
        consecutive_no_bars = 0
        max_consecutive_no_bars = 10  # Stop if no bars for 10 iterations
        
        while self.is_running:
            try:
                if self.is_paused:
                    time.sleep(1.0)
                    continue

                bars_processed = 0
                # Process each symbol - in offline mode, try to get multiple bars per iteration
                for symbol in self.config.symbols:
                    # In offline mode, try to process multiple bars per iteration for speed
                    if is_offline_mode:
                        # Use batch fetching if available (more efficient)
                        if hasattr(self.data_feed, 'get_next_n_bars'):
                            # Batch fetch up to 10 bars at once
                            batch_bars = self.data_feed.get_next_n_bars(symbol, n=10, timeout=0.1)
                            
                            # SYNTHETIC FALLBACK: If no bars and synthetic enabled, generate them
                            if not batch_bars and hasattr(self.data_feed, 'synthetic_enabled') and self.data_feed.synthetic_enabled:
                                logger.info(f"🔄 [LiveLoop] No batch bars for {symbol}, generating synthetic bars")
                                if hasattr(self.data_feed, '_generate_synthetic_bars'):
                                    batch_bars = self.data_feed._generate_synthetic_bars(symbol, count=10)
                                    if batch_bars:
                                        # Add to cached_data so they persist
                                        if symbol not in self.data_feed.cached_data:
                                            self.data_feed.cached_data[symbol] = []
                                        self.data_feed.cached_data[symbol].extend(batch_bars)
                                        logger.info(f"✅ [LiveLoop] Generated {len(batch_bars)} synthetic bars for {symbol}")
                            
                            if batch_bars:
                                # Log first bar timestamp to verify we're processing the correct date
                                if len(batch_bars) > 0:
                                    first_bar_time = batch_bars[0].timestamp
                                    # Verify the bar timestamp matches the selected start_date
                                    if hasattr(self.data_feed, 'start_date') and self.data_feed.start_date:
                                        time_diff = abs((first_bar_time - self.data_feed.start_date).total_seconds())
                                        if time_diff > 3600:  # More than 1 hour difference
                                            logger.warning(f"⚠️ [LiveLoop] First bar timestamp {first_bar_time} differs from start_date {self.data_feed.start_date} by {time_diff/3600:.1f} hours")
                                        else:
                                            logger.info(f"✅ [LiveLoop] First bar timestamp {first_bar_time} matches start_date {self.data_feed.start_date} (diff: {time_diff/60:.1f} min)")
                                    logger.info(f"📅 [LiveLoop] Processing {len(batch_bars)} bars for {symbol}, first bar: {first_bar_time}")
                                for bar in batch_bars:
                                    if not self.is_running:
                                        break
                                    
                                    # CRITICAL FIX: Validate bar symbol matches requested symbol BEFORE processing
                                    if bar.symbol != symbol:
                                        logger.error(f"🚨 [LiveLoop] BATCH SYMBOL MISMATCH: Requested {symbol} but batch bar has symbol {bar.symbol}! Price: {bar.close:.2f}. Skipping this bar.")
                                        continue  # Skip this bar, don't process it
                                    
                                    # Check if bar exceeds end_time (if specified)
                                    if hasattr(self.data_feed, 'end_date') and self.data_feed.end_date:
                                        # Ensure both timestamps are timezone-aware for comparison
                                        bar_ts = bar.timestamp
                                        end_ts = self.data_feed.end_date
                                        
                                        # Make timezone-aware if needed
                                        if bar_ts.tzinfo is None:
                                            from datetime import timezone
                                            bar_ts = bar_ts.replace(tzinfo=timezone.utc)
                                        if end_ts.tzinfo is None:
                                            from datetime import timezone
                                            end_ts = end_ts.replace(tzinfo=timezone.utc)
                                        
                                        if bar_ts > end_ts:
                                            logger.info(f"✅ [LiveLoop] Reached end_time {end_ts} for {symbol} (bar timestamp: {bar_ts})")
                                            self.stop_reason = "end_time_reached"
                                            self.is_running = False
                                            break
                                    
                                    self._process_bar(symbol, bar)
                                    bars_processed += 1
                                    # Ensure symbol case matches exactly (SPY not spy)
                                    symbol_key = symbol.upper() if isinstance(symbol, str) else symbol
                                    old_count = self.bars_per_symbol.get(symbol_key, 0)
                                    self.bars_per_symbol[symbol_key] = old_count + 1
                                    consecutive_no_bars = 0
                                    if self.bars_per_symbol[symbol_key] % 10 == 0:
                                        logger.info(f"✅ [LiveLoop] {symbol_key} bars_per_symbol = {self.bars_per_symbol[symbol_key]} (processed bar #{bars_processed})")
                                        logger.info(f"✅ [LiveLoop] Current state: bar_count={self.bar_count}, bars_per_symbol={self.bars_per_symbol}")
                                
                                # Log progress every 100 bars (reduces I/O overhead)
                                symbol_key = symbol.upper() if isinstance(symbol, str) else symbol
                                if self.bars_per_symbol.get(symbol_key, 0) % 100 == 0:
                                    logger.info(f"🔵 [LiveLoop] {symbol_key} processed {self.bars_per_symbol[symbol_key]} bars so far")
                            else:
                                # No more bars available for this symbol
                                cached_data = getattr(self.data_feed, 'cached_data', {})
                                current_indices = getattr(self.data_feed, 'current_indices', {})
                                if symbol in cached_data:
                                    current_idx = current_indices.get(symbol, 0)
                                    total_bars = len(cached_data.get(symbol, []))
                                    if current_idx >= total_bars:
                                        logger.info(f"✅ [LiveLoop] Finished all {total_bars} cached bars for {symbol}")
                                    else:
                                        logger.debug(f"🔵 [LiveLoop] No bar available for {symbol} (bar {current_idx}/{total_bars})")
                        else:
                            # Fallback to single bar fetching if batch method not available
                            bars_this_iteration = 0
                            max_bars_per_iteration = 10
                            while bars_this_iteration < max_bars_per_iteration and self.is_running:
                                bar = self.data_feed.get_next_bar(symbol, timeout=0.1)
                                
                                # SYNTHETIC FALLBACK: If no bar and synthetic enabled, generate one
                                if not bar and hasattr(self.data_feed, 'synthetic_enabled') and self.data_feed.synthetic_enabled:
                                    logger.debug(f"🔄 No bar for {symbol} in fallback loop, generating synthetic")
                                    if hasattr(self.data_feed, '_generate_synthetic_bars'):
                                        synthetic_bars = self.data_feed._generate_synthetic_bars(symbol, count=1)
                                        if synthetic_bars:
                                            bar = synthetic_bars[0]
                                            logger.info(f"✅ Generated synthetic bar for {symbol} in fallback loop")
                                
                                if bar:
                                    # Check if bar exceeds end_time (if specified)
                                    if hasattr(self.data_feed, 'end_date') and self.data_feed.end_date:
                                        # Ensure both timestamps are timezone-aware for comparison
                                        bar_ts = bar.timestamp
                                        end_ts = self.data_feed.end_date
                                        
                                        # Make timezone-aware if needed
                                        if bar_ts.tzinfo is None:
                                            from datetime import timezone
                                            bar_ts = bar_ts.replace(tzinfo=timezone.utc)
                                        if end_ts.tzinfo is None:
                                            from datetime import timezone
                                            end_ts = end_ts.replace(tzinfo=timezone.utc)
                                        
                                        if bar_ts > end_ts:
                                            logger.info(f"✅ [LiveLoop] Reached end_time {end_ts} for {symbol} (bar timestamp: {bar_ts})")
                                            self.stop_reason = "end_time_reached"
                                            self.is_running = False
                                            break
                                    
                                    self._process_bar(symbol, bar)
                                    bars_processed += 1
                                    bars_this_iteration += 1
                                    # Ensure symbol case matches exactly (SPY not spy)
                                    symbol_key = symbol.upper() if isinstance(symbol, str) else symbol
                                    self.bars_per_symbol[symbol_key] = self.bars_per_symbol.get(symbol_key, 0) + 1
                                    consecutive_no_bars = 0
                                    # Log every 100 bars instead of every bar
                                    if self.bars_per_symbol.get(symbol_key, 0) % 100 == 0:
                                        logger.info(f"🔵 [LiveLoop] {symbol_key} processed {self.bars_per_symbol[symbol_key]} bars so far")
                                else:
                                    # No more bars available
                                    cached_data = getattr(self.data_feed, 'cached_data', {})
                                    current_indices = getattr(self.data_feed, 'current_indices', {})
                                    if symbol in cached_data:
                                        current_idx = current_indices.get(symbol, 0)
                                        total_bars = len(cached_data.get(symbol, []))
                                        if current_idx >= total_bars:
                                            logger.info(f"✅ [LiveLoop] Finished all {total_bars} cached bars for {symbol}")
                                    break
                    else:
                        # Live mode: process one bar per symbol per iteration
                        bar = self.data_feed.get_next_bar(symbol, timeout=1.0)
                        
                        # SYNTHETIC FALLBACK: If no bar returned and synthetic is enabled, generate one
                        if not bar and hasattr(self.data_feed, 'synthetic_enabled') and self.data_feed.synthetic_enabled:
                            logger.debug(f"🔄 No bar from data feed for {symbol}, attempting synthetic fallback")
                            if hasattr(self.data_feed, '_generate_synthetic_bars'):
                                synthetic_bars = self.data_feed._generate_synthetic_bars(symbol, count=1)
                                if synthetic_bars:
                                    bar = synthetic_bars[0]
                                    logger.info(f"✅ Generated synthetic bar for {symbol} in live loop")
                        
                        if bar:
                            # Update last_bar_time immediately when bar is received
                            self.last_bar_time = bar.timestamp
                            self._process_bar(symbol, bar)
                            bars_processed += 1
                            # Ensure symbol case matches exactly (SPY not spy)
                            symbol_key = symbol.upper() if isinstance(symbol, str) else symbol
                            self.bars_per_symbol[symbol_key] = self.bars_per_symbol.get(symbol_key, 0) + 1
                            consecutive_no_bars = 0
                            logger.debug(f"📊 [LiveLoop] Processed bar for {symbol_key}: {bar.timestamp}, Total bars: {self.bars_per_symbol[symbol_key]}")
                        else:
                            logger.debug(f"⚠️ [LiveLoop] No bar available for {symbol} (timeout or no data)")

                # Handle end of data in offline mode
                if is_offline_mode:
                    # Check if all symbols have finished processing
                    all_symbols_done = True
                    cached_data = getattr(self.data_feed, 'cached_data', {})
                    current_indices = getattr(self.data_feed, 'current_indices', {})
                    
                    for sym in self.config.symbols:
                        if sym in cached_data:
                            current_idx = current_indices.get(sym, 0)
                            total_bars = len(cached_data.get(sym, []))
                            if current_idx < total_bars:
                                all_symbols_done = False
                                break
                    
                    if all_symbols_done and bars_processed == 0:
                        # All symbols finished - log summary and stop
                        self._log_simulation_summary()
                        self.stop_reason = "end_of_data"
                        self.is_running = False
                        logger.info(f"✅ [LiveLoop] Simulation complete - all symbols finished processing")
                        break
                    elif bars_processed == 0:
                        consecutive_no_bars += 1
                        if consecutive_no_bars >= max_consecutive_no_bars:
                            # End of data reached - log summary and stop
                            self._log_simulation_summary()
                            self.stop_reason = "end_of_data"
                            self.is_running = False
                            logger.info(f"✅ [LiveLoop] Simulation complete - stopped due to end of data")
                            break
                    else:
                        consecutive_no_bars = 0
                    # In offline mode, use calculated sleep interval (based on replay speed)
                    # Only sleep if we processed bars (to avoid unnecessary delays)
                    if bars_processed > 0:
                        time.sleep(sleep_interval)
                    else:
                        # No bars processed, check more frequently
                        time.sleep(0.01)  # 10ms check interval when no bars
                else:
                    # In live mode, wait for real-time interval
                    time.sleep(sleep_interval)

            except Exception as e:
                error_str = str(e)
                # Don't store VWAP/DatetimeIndex errors (handled with fallback) or KeyError: 0 (handled)
                # Also don't store "cannot convert series to float" errors - these are now handled by safe wrappers
                if ("VWAP" not in error_str and 
                    "DatetimeIndex" not in error_str and 
                    error_str != "0" and
                    "cannot convert the series to" not in error_str):
                    self.error_message = error_str
                    # Log detailed error for debugging
                    import traceback
                    logger.error(f"Error in live trading loop: {e}")
                    logger.error(f"Traceback: {traceback.format_exc()}")
                else:
                    # Clear error message for handled errors
                    self.error_message = None
                    # Log as debug for handled errors
                    if "cannot convert the series to" in error_str:
                        logger.debug(f"Handled conversion error (should not occur with safe wrappers): {error_str}")
                # Continue running but log error
                time.sleep(5.0)

    def _process_bar(self, symbol: str, bar: Bar) -> None:
        """Process a single bar through the full pipeline."""
        # CRITICAL FIX: Validate bar symbol matches requested symbol to prevent cross-symbol contamination
        if bar.symbol != symbol:
            logger.error(f"🚨 [LiveLoop] SYMBOL MISMATCH: Requested {symbol} but bar has symbol {bar.symbol}! Price: {bar.close:.2f}. Discarding bar to prevent incorrect trades.")
            return  # Skip processing this bar to prevent wrong prices being used
        
        self.bar_count += 1
        self.last_bar_time = bar.timestamp
        
        # PERFORMANCE: Reduce logging frequency (every 50 bars instead of 10)
        if self.bar_count % 50 == 0:
            logger.info(f"🔵 [LiveLoop] Processing bar #{self.bar_count} for {symbol} at {bar.timestamp}, price={bar.close:.2f}")

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
        # FORCE MODE: Use testing_mode to allow trading with minimal bars
        min_bars = 1 if self.config.testing_mode else self.config.minimum_bars_required
        if len(bars_df) < min_bars:  # Need enough history for features
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
                    metrics={"bar_count": len(bars_df), "required_bars": min_bars},
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
        # Include previous close for momentum signals
        prev_close = bars_df.iloc[-2]["close"] if len(bars_df) > 1 else latest["close"]
        ema9_val = latest.get("ema9", latest["close"])
        market_state = {
            "close": latest["close"],
            "price": latest["close"],  # Alias for compatibility
            "open": latest["open"],
            "high": latest["high"],
            "low": latest["low"],
            "volume": latest["volume"],
            "ema9": ema9_val,
            "ema_9": ema9_val,  # Alias for compatibility
            "ema21": latest.get("ema21", ema9_val),  # Compute EMA21 if available
            "ema_21": latest.get("ema21", ema9_val),  # Alias
            "rsi": latest.get("rsi", 50.0),
            "atr": latest.get("atr", 0.0),
            "vwap": latest.get("vwap", latest["close"]),
            "vwap_deviation": latest.get("vwap_deviation", 0.0),
            "prev_close": prev_close,  # For momentum signals
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
        
        # ============================================================
        # Calculate GEX Proxy (Gamma Exposure) - Market Microstructure
        # ============================================================
        # GEX measures dealer positioning and is attached to RegimeSignal
        # PERFORMANCE OPTIMIZATION: Cache GEX calculation (update every 5 minutes, not every bar)
        # This makes it accessible to all agents as part of the Market Microstructure Snapshot
        gex_data = None
        if hasattr(self, 'options_data_feed') and self.options_data_feed:
            # Initialize GEX cache if not exists
            if not hasattr(self, '_gex_cache'):
                self._gex_cache = {}
            if not hasattr(self, '_gex_last_update'):
                self._gex_last_update = {}
            
            # Check if we need to update GEX (every 5 minutes = 300 seconds)
            current_time = time.time()
            last_update = self._gex_last_update.get(symbol, 0)
            update_interval = 300  # 5 minutes
            
            if current_time - last_update >= update_interval:
                try:
                    # Fetch options chain for GEX calculation (cached internally by options_data_feed)
                    options_chain = self.options_data_feed.get_options_chain(
                        underlying_symbol=symbol,
                        option_type=None,  # Get both calls and puts for GEX
                    )
                    
                    if options_chain and len(options_chain) > 0:
                        # PERFORMANCE: Sample fewer contracts (50 instead of 100) and skip API calls for quotes/Greeks
                        # Use contract data directly if available, otherwise fetch only what's needed
                        chain_for_gex = []
                        for opt in options_chain[:50]:  # Reduced from 100 to 50 for speed
                            option_symbol_gex = opt.get("symbol", "")
                            if not option_symbol_gex:
                                continue
                            
                            # PERFORMANCE: Try to get data from contract directly first
                            gamma = opt.get('gamma') or 0
                            oi = opt.get('open_interest') or 0
                            
                            # Only fetch quote/Greeks if not in contract data (reduces API calls by ~80%)
                            if gamma == 0 or oi == 0:
                                quote_gex = self.options_data_feed.get_option_quote(option_symbol_gex)
                                greeks_gex = self.options_data_feed.get_option_greeks(option_symbol_gex)
                                if quote_gex:
                                    oi = quote_gex.get('open_interest', 0)
                                if greeks_gex:
                                    gamma = greeks_gex.get('gamma', 0)
                            
                            if gamma > 0 or oi > 0:  # Only include if we have useful data
                                chain_for_gex.append({
                                    'strike_price': opt.get('strike_price', 0),
                                    'option_type': opt.get('option_type', 'call'),
                                    'symbol': option_symbol_gex,
                                    'gamma': gamma,
                                    'open_interest': oi,
                                })
                        
                        if chain_for_gex:
                            # Calculate GEX proxy (GEX v2)
                            gex_data = self.options_data_feed.calculate_gex_proxy(
                                chain_data=chain_for_gex,
                                underlying_price=bar.close,
                            )
                            
                            if gex_data and gex_data.get('gex_coverage', 0) > 0:
                                # Update Market Microstructure singleton
                                self.microstructure.update_gex(symbol, gex_data)
                                
                                # Cache the result
                                self._gex_cache[symbol] = gex_data
                                self._gex_last_update[symbol] = current_time
                                
                                # Only log every 5 minutes (when updated)
                                logger.info(
                                    f"[GEX v2] Updated for {symbol}: regime={gex_data['gex_regime']}, "
                                    f"strength={gex_data['gex_strength']:.2f}B, "
                                    f"coverage={gex_data['gex_coverage']} contracts"
                                )
                except Exception as e:
                    logger.debug(f"Could not calculate GEX proxy for {symbol}: {e}")
            else:
                # Use cached GEX data (much faster)
                gex_data = self._gex_cache.get(symbol)
        
        # Attach GEX data to RegimeSignal (Market Microstructure Snapshot)
        # RegimeSignal is frozen, so we need to create a new one with GEX data
        if gex_data:
            signal = RegimeSignal(
                timestamp=signal.timestamp,
                trend_direction=signal.trend_direction,
                volatility_level=signal.volatility_level,
                regime_type=signal.regime_type,
                bias=signal.bias,
                confidence=signal.confidence,
                active_fvg=signal.active_fvg,
                metrics=signal.metrics,
                is_valid=signal.is_valid,
                gex_regime=gex_data.get('gex_regime'),
                gex_strength=gex_data.get('gex_strength'),
                total_gex_dollar=gex_data.get('total_gex_dollar'),
            )
            # Log GEX for debugging
            if self.bar_count % 10 == 0:  # Log every 10 bars
                logger.info(
                    f"[GEX] regime={gex_data['gex_regime']} strength={gex_data['gex_strength']:.2f}B "
                    f"raw=${gex_data['total_gex_dollar']:,.0f}"
                )
        
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
        if not signal.is_valid and len(bars_df) >= min_bars:
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
        # Pass testing_mode in context so controller can bypass restrictions
        context = {"testing_mode": self.config.testing_mode}
        intent = self.controller.decide(signal, market_state, self.agents, context=context)
        
        # REMOVED: ULTRA FORCE mode that created fake trades
        # Trades will only execute if agents generate valid signals
        
        # Diagnostic logging for trade execution
        logger.info(f"🔍 [TradeDiagnostic] Symbol: {symbol}, Bar: {self.bar_count}")
        logger.info(f"🔍 [TradeDiagnostic] Regime: {signal.regime_type}, Confidence: {signal.confidence:.2f}, Bias: {signal.bias}")
        logger.info(f"🔍 [TradeDiagnostic] Intent valid: {intent.is_valid}, Position delta: {intent.position_delta:.4f}, Confidence: {intent.confidence:.2f}")
        logger.info(f"🔍 [TradeDiagnostic] Reason: {intent.reason}")

        # Get current position from broker
        positions = self.executor.broker_client.get_positions(symbol)
        current_position = positions[0].quantity if positions else 0.0
        
        # Check profit-taking for existing positions
        if self.profit_manager and current_position != 0:
            # CRITICAL FIX: Use bar.close for profit manager check
            should_close, reason = self.profit_manager.should_take_profit(
                symbol, bar.close, self.bar_count, signal
            )
            if should_close:
                logger.info(f"Taking profit for {symbol}: {reason}")
                # Close position
                # CRITICAL FIX: Pass bar.close as current_price for correct fill price
                result = self.executor.close_position(symbol, current_position, current_price=bar.close)
                if result.success:
                    # Update portfolio
                    if symbol in self.portfolio.positions:
                        # Use stored regime/volatility from position
                        # CRITICAL FIX: Use bar.close directly to ensure correct price
                        trade = self.portfolio.close_position(
                            symbol, bar.close, bar.timestamp, reason, "profit_manager",
                            regime_at_entry=None,  # Use stored from position
                            vol_bucket_at_entry=None,  # Use stored from position
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

        # Advanced risk check - BYPASS in testing_mode
        if self.advanced_risk and not self.config.testing_mode:
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
        elif self.config.testing_mode:
            logger.info(f"🔥 [TestingMode] Bypassing advanced risk check - forcing trade execution")

        # FORCE MODE: In testing_mode, force execution even if intent is invalid
        if self.config.testing_mode and not intent.is_valid:
            logger.info(f"🔥 [TestingMode] Intent invalid but forcing execution: {intent.reason}")
            # Create a valid intent with minimum position delta
            if intent.position_delta == 0:
                intent = intent.__class__(
                    position_delta=0.1,  # Force minimum position
                    confidence=max(0.1, intent.confidence),
                    primary_agent=intent.primary_agent or "trend_agent",
                    contributing_agents=intent.contributing_agents or ["trend_agent"],
                    reason=f"FORCED: {intent.reason}",
                    is_valid=True,
                )
            else:
                # Make intent valid
                intent = intent.__class__(
                    position_delta=intent.position_delta,
                    confidence=max(0.1, intent.confidence),
                    primary_agent=intent.primary_agent or "trend_agent",
                    contributing_agents=intent.contributing_agents or ["trend_agent"],
                    reason=f"FORCED: {intent.reason}",
                    is_valid=True,
                )
        
        # Execute if valid - route to options or stock executor
        if intent.is_valid and intent.position_delta != 0:
            # Check if this is an options trade
            if intent.instrument_type == "option":
                logger.info(f"✅ [OptionsExecution] Executing options trade: {symbol}, Type: {intent.option_type}, Delta: {intent.position_delta:.4f}, Reason: {intent.reason}")
                # Get current option position if exists (simplified - in production track better)
                current_option_pos = None
                
                # Get regime/volatility strings
                regime_str = signal.regime_type.value if hasattr(signal.regime_type, 'value') else str(signal.regime_type)
                vol_str = signal.volatility_level.value if hasattr(signal.volatility_level, 'value') else str(signal.volatility_level)
                
                # Execute options trade
                result = self.options_executor.execute_intent(
                    intent=intent,
                    symbol=symbol,
                    underlying_price=bar.close,
                    current_position=current_option_pos,
                    regime_at_entry=regime_str,
                    vol_bucket_at_entry=vol_str,
                )
                
                if result.success:
                    if result.trade:
                        logger.info(f"✅ [OptionsExecution] Closed options position: {result.option_symbol}, P&L: ${result.trade.pnl:.2f}")
                    elif result.option_position:
                        logger.info(f"✅ [OptionsExecution] Opened options position: {result.option_symbol}, Quantity: {result.option_position.quantity:.2f} contracts")
                    
                    # Track multi-leg positions for profit management
                    if intent.option_type in ("straddle", "strangle") and result.option_symbol:
                        # Extract strategy from metadata
                        strategy = metadata.get("strategy", "unknown")
                        direction = "short" if intent.position_delta < 0 else "long"
                        net_premium = metadata.get("total_credit", 0) if direction == "short" else metadata.get("total_debit", 0)
                        
                        # Get entry IV and GEX
                        entry_iv = None
                        entry_gex = None
                        if self.options_data_feed:
                            # Try to get IV from call option
                            call_symbol = metadata.get("call_symbol", "")
                            if call_symbol:
                                greeks = self.options_data_feed.get_option_greeks(call_symbol)
                                if greeks:
                                    entry_iv = greeks.get("implied_volatility")
                        
                        if hasattr(signal, 'gex_strength'):
                            entry_gex = signal.gex_strength
                        
                        self.multi_leg_profit_manager.track_position(
                            multi_leg_id=result.option_symbol,
                            strategy=strategy,
                            direction=direction,
                            net_premium=net_premium,
                            entry_time=datetime.now(),
                            entry_bar=self.bar_count,
                            entry_iv=entry_iv,
                            entry_gex_strength=entry_gex,
                        )
                else:
                    logger.warning(f"⚠️ [OptionsExecution] Options trade failed: {result.reason}")
                
                # Update options positions with current prices
                self.options_executor.update_positions(symbol, bar.close)
                
                # Check multi-leg profit exits
                self._check_multi_leg_exits(symbol, bar.close, signal)
                
                return  # Options trades handled, skip stock execution
            
            # Stock trade execution (existing logic)
            logger.info(f"✅ [TradeExecution] Executing trade: {symbol}, Delta: {intent.position_delta:.4f}, Reason: {intent.reason}")
            # Get investment amount from asset profile or config
            if self.asset_profiles and symbol in self.asset_profiles:
                profile = self.asset_profiles[symbol]
                base_investment = profile.fixed_investment_amount or self.config.fixed_investment_amount
            else:
                base_investment = self.config.fixed_investment_amount
            
            # Calculate target quantity based on investment amount
            # CRITICAL FIX: Use bar.close for quantity calculation to ensure correct price
            target_quantity = base_investment / bar.close if bar.close > 0 else 0.0
            
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
                # In testing mode, use simpler position sizing to ensure full investment
                if self.config.testing_mode:
                    # For testing: use full base_investment (or 80% minimum for very low confidence)
                    # This ensures we see realistic position sizes for validation
                    confidence_factor = max(0.8, intent.confidence) if intent.confidence > 0 else 0.8
                    adjusted_size = base_investment * confidence_factor
                else:
                    # Production: use full advanced risk management
                    size, _ = self.advanced_risk.compute_advanced_position_size(
                        base_investment,
                        bar.close,
                        intent.confidence,
                        signal.regime_type,
                        signal.volatility_level,
                        self.bar_count,
                    )
                    adjusted_size = size
                
                # Convert dollar size to quantity
                max_quantity = adjusted_size / bar.close if bar.close > 0 else 0.0
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
                # CRITICAL FIX: position_delta is already in SHARES, don't divide by price again!
                # The position_delta was calculated as target_quantity - current_position (both in shares)
                modified_intent = intent.__class__(
                    position_delta=position_delta,  # Already in shares, NOT dollars!
                    confidence=intent.confidence,
                    primary_agent=intent.primary_agent,
                    contributing_agents=intent.contributing_agents,
                    reason=f"{intent.reason} (${base_investment:.0f} investment)",
                    is_valid=True,
                )
                
                # CRITICAL FIX: Log symbol and price before execution to catch mismatches
                logger.info(f"🔍 [TradeExecution] Executing trade for {symbol}: bar.symbol={bar.symbol}, bar.close=${bar.close:.2f}, intent.delta={intent.position_delta:.4f}")
                if bar.symbol != symbol:
                    logger.error(f"🚨 [TradeExecution] CRITICAL: Symbol mismatch detected! Requested {symbol} but bar.symbol={bar.symbol}, price=${bar.close:.2f}. ABORTING TRADE.")
                    return  # Skip this trade to prevent wrong prices (return from function, not continue)
                
                # Use bar.close directly to ensure correct price (not latest["close"] which might be from wrong bar)
                result = self.executor.apply_intent(modified_intent, symbol, bar.close, current_position, risk_constraints)
                if result.success and result.order:
                    # Determine if this is a buy or sell
                    is_buy = result.position_delta_applied > 0
                    side = "BUY" if is_buy else "SELL"
                    quantity = abs(result.position_delta_applied)
                    # CRITICAL FIX: Use bar.close directly to ensure correct price from the actual bar being processed
                    price = bar.close
                    
                    # CRITICAL FIX: Log final trade details to verify correct symbol and price
                    logger.info(f"✅ [TradeExecution] Trade executed: {symbol} {side} {quantity:.4f} @ ${price:.2f} (bar.symbol={bar.symbol}, verified match)")
                    
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
                    
                    # Update portfolio with regime/volatility metadata
                    regime_str = signal.regime_type.value if hasattr(signal.regime_type, 'value') else str(signal.regime_type)
                    vol_str = signal.volatility_level.value if hasattr(signal.volatility_level, 'value') else str(signal.volatility_level)
                    # CRITICAL FIX: Use bar.close directly to ensure correct price
                    trade = self.portfolio.apply_position_delta(
                        result.position_delta_applied, 
                        bar.close,  # Use actual bar price, not latest["close"]
                        bar.timestamp,
                        regime_at_entry=regime_str,
                        vol_bucket_at_entry=vol_str,
                    )
                    
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
                                entry_price = bar.close  # Use actual bar price
                            
                            self.profit_manager.track_position(
                                symbol=symbol,
                                entry_price=entry_price,
                                quantity=new_position,
                                entry_time=bar.timestamp,
                                entry_bar=self.bar_count,
                            )

        # Update portfolio equity - CRITICAL FIX: Use bar.close directly
        self.portfolio.update_position(symbol, bar.close)
        self.portfolio.record_equity(bar.close)
        
        # Update options positions with current underlying price
        self.options_executor.update_positions(symbol, bar.close)
        
        # Check multi-leg profit exits
        self._check_multi_leg_exits(symbol, bar.close, signal)
        
        # Update profit manager
        if self.profit_manager:
            self.profit_manager.update_position(symbol, bar.close, self.bar_count)

        # Update advanced risk equity
        if self.advanced_risk:
            total_value = self.portfolio.get_total_value(bar.close)
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
        # Compute slope and r_squared using rolling_regression
        # Handle the case where rolling_regression might return empty DataFrame or Series
        def safe_rolling_slope(x):
            if len(x) < 10:
                return 0.0
            try:
                result = stats_features.rolling_regression(x, window=min(30, len(x)))
                if result.empty or len(result) == 0:
                    return 0.0
                slope_val = result["slope"].iloc[-1]
                # Ensure we return a scalar float, not a Series
                if isinstance(slope_val, pd.Series):
                    slope_val = slope_val.iloc[-1] if len(slope_val) > 0 else 0.0
                return float(slope_val) if pd.notna(slope_val) else 0.0
            except (IndexError, KeyError, ValueError, TypeError) as e:
                logger.debug(f"Error computing slope: {e}")
                return 0.0
        
        def safe_rolling_r2(x):
            if len(x) < 10:
                return 0.0
            try:
                result = stats_features.rolling_regression(x, window=min(30, len(x)))
                if result.empty or len(result) == 0:
                    return 0.0
                r2_val = result["r_squared"].iloc[-1]
                # Ensure we return a scalar float, not a Series
                if isinstance(r2_val, pd.Series):
                    r2_val = r2_val.iloc[-1] if len(r2_val) > 0 else 0.0
                return float(r2_val) if pd.notna(r2_val) else 0.0
            except (IndexError, KeyError, ValueError, TypeError) as e:
                logger.debug(f"Error computing r_squared: {e}")
                return 0.0
        
        df["slope"] = df["close"].rolling(30, min_periods=10).apply(safe_rolling_slope, raw=False).fillna(0.0)
        df["r_squared"] = df["close"].rolling(30, min_periods=10).apply(safe_rolling_r2, raw=False).fillna(0.0)

        df["atr_pct"] = (df["atr"] / df["close"]) * 100.0
        df["vwap_deviation"] = ((df["close"] - df["vwap"]) / df["vwap"]) * 100.0
        df["minute_displacement"] = stats_features.minute_displacement(df)
        df["iv_proxy"] = df["atr_pct"] * 1.5  # Simple proxy

        return df
    
    def _check_multi_leg_exits(
        self,
        symbol: str,
        underlying_price: float,
        signal: RegimeSignal,
    ) -> None:
        """Check and execute exits for multi-leg positions."""
        if not self.multi_leg_profit_manager:
            return
        
        # Get all open multi-leg positions for this symbol
        multi_leg_positions = self.options_portfolio.get_all_multi_leg_positions()
        symbol_positions = [ml_pos for ml_pos in multi_leg_positions if ml_pos.symbol == symbol]
        
        for ml_pos in symbol_positions:
            # Calculate current P&L percentage
            current_pnl_pct = (ml_pos.combined_unrealized_pnl / ml_pos.net_premium * 100.0) if ml_pos.net_premium > 0 else 0.0
            
            # Check if should exit
            should_close, reason = self.multi_leg_profit_manager.should_take_profit(
                multi_leg_id=ml_pos.multi_leg_id,
                current_pnl_pct=current_pnl_pct,
                current_bar=self.bar_count,
                current_regime=signal,
                symbol=symbol,
            )
            
            if should_close:
                logger.info(
                    f"🔔 [MultiLegExit] Closing {ml_pos.trade_type.upper()} {ml_pos.multi_leg_id}: {reason}"
                )
                
                # Close the multi-leg position
                trade = self.options_executor.close_multi_leg_position(
                    multi_leg_id=ml_pos.multi_leg_id,
                    underlying_price=underlying_price,
                    reason=reason,
                    agent=ml_pos.multi_leg_id.split("_")[1] if "_" in ml_pos.multi_leg_id else "system",
                )
                
                if trade:
                    logger.info(
                        f"✅ [MultiLegExit] Closed {ml_pos.trade_type.upper()}: "
                        f"P&L=${trade.combined_pnl:.2f} ({trade.combined_pnl_pct:.1f}%)"
                    )
                    
                    # Stop tracking
                    self.multi_leg_profit_manager.remove_position(ml_pos.multi_leg_id)
                    
                    # Send notification if available
                    if self.notification_service:
                        try:
                            self.notification_service.send_trade_notification(
                                symbol=symbol,
                                side="CLOSE",
                                quantity=ml_pos.call_quantity + ml_pos.put_quantity,
                                price=underlying_price,
                                order_id=None,
                                pnl=trade.combined_pnl,
                                pnl_pct=trade.combined_pnl_pct,
                            )
                        except Exception as e:
                            logger.error(f"Failed to send multi-leg close notification: {e}")

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
        """Get current status of the live trading loop."""
        status = {
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "bar_count": self.bar_count,
            "last_bar_time": self.last_bar_time.isoformat() if self.last_bar_time else None,
            "error": self.error_message,
            "stop_reason": self.stop_reason,
            "bars_per_symbol": self.bars_per_symbol,
        }
        
        # Add duration if started
        if self.start_time:
            from datetime import datetime, timezone
            duration = (datetime.now(timezone.utc) - self.start_time).total_seconds()
            status["duration_seconds"] = duration
        
        return status

