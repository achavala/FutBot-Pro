"""Synthetic options trade executor."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import logging

from core.options.pricing import SyntheticOptionsPricer
from core.policy.types import FinalTradeIntent
from core.portfolio.options_manager import OptionsPortfolioManager, OptionPosition, OptionTrade

logger = logging.getLogger(__name__)


@dataclass
class OptionsExecutionResult:
    """Result of options trade execution."""

    success: bool
    option_position: Optional[OptionPosition] = None
    trade: Optional[OptionTrade] = None
    reason: str = ""
    option_symbol: str = ""


class SyntheticOptionsExecutor:
    """
    Executes options trades using real Alpaca broker when available, synthetic pricing as fallback.
    
    Supports:
    - Real Alpaca paper trading orders (when options_broker_client provided)
    - Synthetic execution (when no broker client)
    - Real market data from options_data_feed
    """

    def __init__(
        self, 
        options_portfolio: OptionsPortfolioManager, 
        options_data_feed=None,
        options_broker_client=None,  # OptionsBrokerClient for real Alpaca orders
    ):
        self.options_portfolio = options_portfolio
        self.pricer = SyntheticOptionsPricer()
        self.options_data_feed = options_data_feed  # Real options data feed (if available)
        self.options_broker_client = options_broker_client  # Real broker client for Alpaca orders
        self.default_iv = 0.20  # 20% default IV
        self.default_risk_free_rate = 0.05  # 5% risk-free rate
        
        if self.options_broker_client:
            logger.info("✅ OptionsExecutor: Real Alpaca broker client enabled - will place actual orders")
        else:
            logger.info("⚠️ OptionsExecutor: No broker client - using synthetic execution only")

    def execute_intent(
        self,
        intent: FinalTradeIntent,
        symbol: str,
        underlying_price: float,
        current_position: Optional[OptionPosition] = None,
        regime_at_entry: Optional[str] = None,
        vol_bucket_at_entry: Optional[str] = None,
    ) -> OptionsExecutionResult:
        """
        Execute an options trade intent.
        
        Args:
            intent: FinalTradeIntent with options metadata
            symbol: Underlying symbol (e.g., "QQQ")
            underlying_price: Current underlying price
            current_position: Existing option position (if any)
            regime_at_entry: Regime at entry
            vol_bucket_at_entry: Volatility bucket at entry
        
        Returns:
            OptionsExecutionResult
        """
        if not intent.is_valid or intent.instrument_type != "option":
            return OptionsExecutionResult(success=False, reason="Invalid intent or not an options trade")

        if not intent.option_type:
            return OptionsExecutionResult(success=False, reason="Missing option_type")
        
        # Handle multi-leg trades (straddles and strangles)
        if intent.option_type in ("straddle", "strangle"):
            return self._execute_multi_leg_trade(
                intent=intent,
                symbol=symbol,
                underlying_price=underlying_price,
                regime_at_entry=regime_at_entry,
                vol_bucket_at_entry=vol_bucket_at_entry,
            )
        
        # For single-leg options, continue with existing logic

        # Calculate strike from moneyness
        moneyness = intent.moneyness or "atm"
        strike = self.pricer.calculate_strike_from_moneyness(underlying_price, moneyness, intent.option_type)

        # Calculate expiration from DTE
        dte = intent.time_to_expiry_days or 0
        time_to_expiry = self.pricer.calculate_expiration_from_dte(dte)
        expiration = datetime.now() + timedelta(days=dte)

        # CRITICAL: Use real option data if available from intent metadata
        option_symbol = None
        option_price = None
        greeks = None
        
        # Check if intent has real option data from options agent
        if intent.metadata and "option_symbol" in intent.metadata:
            option_symbol = intent.metadata["option_symbol"]
            logger.info(f"✅ [OptionsExecutor] Using REAL option: {option_symbol}")
            
            # Try to get real quote and Greeks from data feed
            if self.options_data_feed:
                quote = self.options_data_feed.get_option_quote(option_symbol)
                greeks_data = self.options_data_feed.get_option_greeks(option_symbol)
                
                if quote and greeks_data:
                    # Use real market price (mid of bid/ask)
                    bid = quote.get("bid", 0)
                    ask = quote.get("ask", 0)
                    if bid > 0 and ask > 0:
                        option_price = (bid + ask) / 2.0
                        logger.info(f"✅ [OptionsExecutor] Real option price: ${option_price:.2f} (bid=${bid:.2f}, ask=${ask:.2f})")
                    else:
                        option_price = quote.get("last", 0)
                        logger.info(f"✅ [OptionsExecutor] Real option price (last): ${option_price:.2f}")
                    
                    # Use real Greeks
                    greeks = {
                        "delta": greeks_data.get("delta", 0.0),
                        "gamma": greeks_data.get("gamma", 0.0),
                        "theta": greeks_data.get("theta", 0.0),
                        "vega": greeks_data.get("vega", 0.0),
                        "implied_volatility": greeks_data.get("implied_volatility", self.default_iv),
                    }
                    logger.info(f"✅ [OptionsExecutor] Real Greeks: Δ={greeks['delta']:.3f}, IV={greeks['implied_volatility']:.2%}")
                else:
                    logger.warning(f"⚠️ [OptionsExecutor] Real option symbol provided but no quote/Greeks available, using synthetic")
        
        # Fallback to synthetic pricing if no real data
        if option_price is None:
            logger.info(f"📊 [OptionsExecutor] Using SYNTHETIC pricing (no real option data)")
            option_price = self.pricer.calculate_option_price(
                underlying_price=underlying_price,
                strike=strike,
                time_to_expiry=time_to_expiry,
                iv=self.default_iv,
                option_type=intent.option_type,
                risk_free_rate=self.default_risk_free_rate,
            )
        
        if greeks is None:
            greeks = self.pricer.calculate_greeks(
                underlying_price=underlying_price,
                strike=strike,
                time_to_expiry=time_to_expiry,
                iv=self.default_iv,
                option_type=intent.option_type,
                current_price=option_price,
            )
        
        # Generate option symbol if not provided
        if not option_symbol:
            option_symbol = self._generate_option_symbol(symbol, intent.option_type, strike, expiration, moneyness)

        # Determine quantity (number of contracts)
        # For options, position_delta represents number of contracts
        # Positive = buy, negative = sell
        quantity = intent.position_delta
        
        # Determine order side
        order_side = "buy" if quantity > 0 else "sell"
        quantity_abs = int(abs(quantity))
        
        # ============================================================
        # REAL ALPACA ORDER EXECUTION (if broker client available)
        # ============================================================
        # Safety check: Skip real orders if marked as SIM-only
        # (e.g., straddle selling in Alpaca paper trading)
        is_sim_only = intent.metadata and intent.metadata.get("sim_only", False)
        if is_sim_only:
            logger.info(
                f"⚠️ [SIM ONLY] Skipping real order for {option_symbol} - "
                f"marked as simulation-only: {intent.metadata.get('reason', 'N/A')}"
            )
            # Fall through to synthetic execution below
        
        if self.options_broker_client and option_symbol and len(option_symbol) > 10 and not is_sim_only:
            # Real option symbol (e.g., "SPY251126P00673000") - place real order
            try:
                from core.live.types import OrderSide
                
                side = OrderSide.BUY if quantity > 0 else OrderSide.SELL
                
                # Use real market price or limit price
                limit_price = None
                if intent.metadata and "limit_price" in intent.metadata:
                    limit_price = float(intent.metadata["limit_price"])
                elif option_price > 0:
                    # Use current option price as limit for safety
                    limit_price = option_price
                
                logger.info(
                    f"📤 [REAL ORDER] Submitting {order_side.upper()} {quantity_abs} contracts "
                    f"of {option_symbol} @ ${limit_price:.2f if limit_price else 'MARKET'}"
                )
                
                # Submit real order to Alpaca
                from core.live.types import OrderType
                # Use limit order if limit_price provided, otherwise market order
                order_type = OrderType.LIMIT if limit_price else OrderType.MARKET
                
                order = self.options_broker_client.submit_options_order(
                    option_symbol=option_symbol,
                    side=side,
                    quantity=quantity_abs,
                    order_type=order_type,
                    limit_price=limit_price,
                )
                
                logger.info(
                    f"✅ [REAL ORDER] Order submitted: {order.order_id}, "
                    f"Status: {order.status}, "
                    f"Filled: {order.filled_quantity}/{quantity_abs} @ ${order.filled_price:.2f}"
                )
                
                # Update portfolio with real order results
                if order.status in ["filled", "partially_filled"]:
                    # Create position from real order
                    pos = self.options_portfolio.add_position(
                        symbol=symbol,
                        option_symbol=option_symbol,
                        option_type=intent.option_type,
                        strike=strike,
                        expiration=expiration,
                        quantity=order.filled_quantity if quantity > 0 else -order.filled_quantity,
                        entry_price=order.filled_price,
                        entry_time=datetime.now(),
                        underlying_price=underlying_price,
                        delta=greeks["delta"],
                        theta=greeks["theta"],
                        iv=greeks["iv"],
                        regime_at_entry=regime_at_entry,
                        vol_bucket_at_entry=vol_bucket_at_entry,
                    )
                    return OptionsExecutionResult(
                        success=True,
                        option_position=pos,
                        reason=f"Real Alpaca order filled: {order.filled_quantity} contracts @ ${order.filled_price:.2f}",
                        option_symbol=option_symbol,
                    )
                else:
                    # Order pending
                    return OptionsExecutionResult(
                        success=True,
                        reason=f"Real Alpaca order submitted: {order.status}",
                        option_symbol=option_symbol,
                    )
                    
            except Exception as e:
                logger.error(f"❌ [REAL ORDER] Failed to submit Alpaca order: {e}", exc_info=True)
                # Fall through to synthetic execution
                logger.info("⚠️ [REAL ORDER] Falling back to synthetic execution")

        # If we have an existing position, check if we're closing it
        if current_position and current_position.option_symbol == option_symbol:
            # Same option - update position or close if reversing
            if (current_position.quantity > 0 and quantity < 0) or (current_position.quantity < 0 and quantity > 0):
                # Closing position
                trade = self.options_portfolio.close_position(
                    option_symbol=option_symbol,
                    exit_price=option_price,
                    exit_time=datetime.now(),
                    underlying_price=underlying_price,
                    reason=intent.reason,
                    agent=intent.primary_agent,
                )
                return OptionsExecutionResult(
                    success=True,
                    trade=trade,
                    reason=f"Closed {intent.option_type} position",
                    option_symbol=option_symbol,
                )
            else:
                # Adding to position
                self.options_portfolio.add_position(
                    symbol=symbol,
                    option_symbol=option_symbol,
                    option_type=intent.option_type,
                    strike=strike,
                    expiration=expiration,
                    quantity=quantity,
                    entry_price=option_price,
                    entry_time=datetime.now(),
                    underlying_price=underlying_price,
                    delta=greeks["delta"],
                    theta=greeks["theta"],
                    iv=greeks["iv"],
                    regime_at_entry=regime_at_entry,
                    vol_bucket_at_entry=vol_bucket_at_entry,
                )
                pos = self.options_portfolio.get_position(option_symbol)
                return OptionsExecutionResult(
                    success=True,
                    option_position=pos,
                    reason=f"Added to {intent.option_type} position",
                    option_symbol=option_symbol,
                )
        else:
            # New position
            pos = self.options_portfolio.add_position(
                symbol=symbol,
                option_symbol=option_symbol,
                option_type=intent.option_type,
                strike=strike,
                expiration=expiration,
                quantity=quantity,
                entry_price=option_price,
                entry_time=datetime.now(),
                underlying_price=underlying_price,
                delta=greeks["delta"],
                theta=greeks["theta"],
                iv=greeks["iv"],
                regime_at_entry=regime_at_entry,
                vol_bucket_at_entry=vol_bucket_at_entry,
            )
            return OptionsExecutionResult(
                success=True,
                option_position=pos,
                reason=f"Opened new {intent.option_type} position",
                option_symbol=option_symbol,
            )

    def update_positions(self, symbol: str, underlying_price: float) -> None:
        """Update all option positions for a symbol with current prices."""
        positions = self.options_portfolio.get_all_positions()
        for pos in positions:
            if pos.symbol == symbol:
                # Recalculate option price
                time_to_expiry = pos.days_to_expiry / 365.0
                option_price = self.pricer.calculate_option_price(
                    underlying_price=underlying_price,
                    strike=pos.strike,
                    time_to_expiry=time_to_expiry,
                    iv=pos.iv,
                    option_type=pos.option_type,
                    risk_free_rate=self.default_risk_free_rate,
                )

                # Recalculate Greeks
                greeks = self.pricer.calculate_greeks(
                    underlying_price=underlying_price,
                    strike=pos.strike,
                    time_to_expiry=time_to_expiry,
                    iv=pos.iv,
                    option_type=pos.option_type,
                    current_price=option_price,
                )

                # Update position
                self.options_portfolio.update_position(
                    option_symbol=pos.option_symbol,
                    underlying_price=underlying_price,
                    option_price=option_price,
                    delta=greeks["delta"],
                    theta=greeks["theta"],
                    iv=greeks["iv"],
                )

                # Check for expiration
                if pos.is_expired:
                    logger.info(f"Option {pos.option_symbol} expired, closing position")
                    self.options_portfolio.close_position(
                        option_symbol=pos.option_symbol,
                        exit_price=option_price,  # Final intrinsic value
                        exit_time=datetime.now(),
                        underlying_price=underlying_price,
                        reason="Expired",
                        agent="system",
                    )

    def close_position(
        self,
        option_symbol: str,
        underlying_price: float,
        reason: str = "Manual close",
    ) -> Optional[OptionTrade]:
        """Close an option position."""
        pos = self.options_portfolio.get_position(option_symbol)
        if not pos:
            return None

        # Calculate current option price
        time_to_expiry = pos.days_to_expiry / 365.0
        option_price = self.pricer.calculate_option_price(
            underlying_price=underlying_price,
            strike=pos.strike,
            time_to_expiry=time_to_expiry,
            iv=pos.iv,
            option_type=pos.option_type,
            risk_free_rate=self.default_risk_free_rate,
        )

        return self.options_portfolio.close_position(
            option_symbol=option_symbol,
            exit_price=option_price,
            exit_time=datetime.now(),
            underlying_price=underlying_price,
            reason=reason,
            agent="system",
        )
    
    def close_multi_leg_position(
        self,
        multi_leg_id: str,
        underlying_price: float,
        reason: str = "Manual close",
        agent: str = "system",
    ) -> Optional["MultiLegTrade"]:
        """
        Close a multi-leg position (straddle or strangle) as a package.
        
        This closes both legs simultaneously and creates a combined trade record.
        """
        from core.portfolio.options_manager import MultiLegTrade, LegFill
        from core.live.types import OrderSide, OrderType
        
        ml_pos = self.options_portfolio.get_multi_leg_position(multi_leg_id)
        if not ml_pos:
            logger.warning(f"⚠️ [MultiLeg] Position {multi_leg_id} not found")
            return None
        
        if not ml_pos.both_legs_filled:
            logger.warning(f"⚠️ [MultiLeg] Cannot close {multi_leg_id} - legs not fully filled")
            return None
        
        # Get current prices for both legs
        call_exit_price = None
        put_exit_price = None
        
        if self.options_data_feed:
            call_quote = self.options_data_feed.get_option_quote(ml_pos.call_option_symbol)
            put_quote = self.options_data_feed.get_option_quote(ml_pos.put_option_symbol)
            
            if call_quote and put_quote:
                # For closing: opposite side of entry
                # If we sold (short), we buy back (use ask)
                # If we bought (long), we sell (use bid)
                if ml_pos.direction == "short":
                    call_exit_price = float(call_quote.get("ask", 0))
                    put_exit_price = float(put_quote.get("ask", 0))
                else:
                    call_exit_price = float(call_quote.get("bid", 0))
                    put_exit_price = float(put_quote.get("bid", 0))
        
        # Fallback to synthetic pricing if no real data
        if call_exit_price is None or call_exit_price <= 0:
            time_to_expiry = ml_pos.days_to_expiry / 365.0
            call_exit_price = self.pricer.calculate_option_price(
                underlying_price=underlying_price,
                strike=ml_pos.call_strike,
                time_to_expiry=time_to_expiry,
                iv=ml_pos.call_iv,
                option_type="call",
                risk_free_rate=self.default_risk_free_rate,
            )
        
        if put_exit_price is None or put_exit_price <= 0:
            time_to_expiry = ml_pos.days_to_expiry / 365.0
            put_exit_price = self.pricer.calculate_option_price(
                underlying_price=underlying_price,
                strike=ml_pos.put_strike,
                time_to_expiry=time_to_expiry,
                iv=ml_pos.put_iv,
                option_type="put",
                risk_free_rate=self.default_risk_free_rate,
            )
        
        logger.info(
            f"🔵 [MultiLeg] Closing {ml_pos.trade_type.upper()} {multi_leg_id}:\n"
            f"   CALL: {ml_pos.call_quantity}x @ ${call_exit_price:.2f}\n"
            f"   PUT: {ml_pos.put_quantity}x @ ${put_exit_price:.2f}\n"
            f"   Reason: {reason}"
        )
        
        # ============================================================
        # SUBMIT CLOSING ORDERS FOR BOTH LEGS
        # ============================================================
        call_exit_fill = None
        put_exit_fill = None
        
        # Determine closing side (opposite of entry)
        closing_side = OrderSide.BUY if ml_pos.direction == "short" else OrderSide.SELL
        
        if self.options_broker_client:
            try:
                # Submit call closing order
                logger.info(
                    f"📤 [MultiLeg] Submitting CALL closing order: "
                    f"{closing_side.value} {ml_pos.call_quantity} contracts of {ml_pos.call_option_symbol}"
                )
                call_exit_order = self.options_broker_client.submit_options_order(
                    option_symbol=ml_pos.call_option_symbol,
                    side=closing_side,
                    quantity=ml_pos.call_quantity,
                    order_type=OrderType.LIMIT,
                    limit_price=call_exit_price,
                )
                
                # Submit put closing order
                logger.info(
                    f"📤 [MultiLeg] Submitting PUT closing order: "
                    f"{closing_side.value} {ml_pos.put_quantity} contracts of {ml_pos.put_option_symbol}"
                )
                put_exit_order = self.options_broker_client.submit_options_order(
                    option_symbol=ml_pos.put_option_symbol,
                    side=closing_side,
                    quantity=ml_pos.put_quantity,
                    order_type=OrderType.LIMIT,
                    limit_price=put_exit_price,
                )
                
                # Track exit fills
                call_exit_fill = LegFill(
                    leg_type="call",
                    option_symbol=ml_pos.call_option_symbol,
                    strike=ml_pos.call_strike,
                    quantity=call_exit_order.filled_quantity if call_exit_order.filled_quantity > 0 else ml_pos.call_quantity,
                    fill_price=call_exit_order.filled_price if call_exit_order.filled_price > 0 else call_exit_price,
                    fill_time=datetime.now(),
                    order_id=call_exit_order.order_id,
                    status=call_exit_order.status.value if hasattr(call_exit_order.status, 'value') else str(call_exit_order.status),
                )
                
                put_exit_fill = LegFill(
                    leg_type="put",
                    option_symbol=ml_pos.put_option_symbol,
                    strike=ml_pos.put_strike,
                    quantity=put_exit_order.filled_quantity if put_exit_order.filled_quantity > 0 else ml_pos.put_quantity,
                    fill_price=put_exit_order.filled_price if put_exit_order.filled_price > 0 else put_exit_price,
                    fill_time=datetime.now(),
                    order_id=put_exit_order.order_id,
                    status=put_exit_order.status.value if hasattr(put_exit_order.status, 'value') else str(put_exit_order.status),
                )
                
                logger.info(
                    f"✅ [MultiLeg] CALL exit fill: {call_exit_fill.quantity} @ ${call_exit_fill.fill_price:.2f} "
                    f"(status: {call_exit_fill.status})"
                )
                logger.info(
                    f"✅ [MultiLeg] PUT exit fill: {put_exit_fill.quantity} @ ${put_exit_fill.fill_price:.2f} "
                    f"(status: {put_exit_fill.status})"
                )
                
            except Exception as e:
                logger.error(f"❌ [MultiLeg] Failed to submit closing orders: {e}", exc_info=True)
                # Fall through to synthetic execution
        
        # If no real fills, use synthetic
        if call_exit_fill is None or put_exit_fill is None:
            call_exit_fill = LegFill(
                leg_type="call",
                option_symbol=ml_pos.call_option_symbol,
                strike=ml_pos.call_strike,
                quantity=ml_pos.call_quantity,
                fill_price=call_exit_price,
                fill_time=datetime.now(),
                status="filled",
            )
            
            put_exit_fill = LegFill(
                leg_type="put",
                option_symbol=ml_pos.put_option_symbol,
                strike=ml_pos.put_strike,
                quantity=ml_pos.put_quantity,
                fill_price=put_exit_price,
                fill_time=datetime.now(),
                status="filled",
            )
        
        # Close the multi-leg position
        trade = self.options_portfolio.close_multi_leg_position(
            multi_leg_id=multi_leg_id,
            call_exit_price=call_exit_fill.fill_price,
            put_exit_price=put_exit_fill.fill_price,
            exit_time=datetime.now(),
            underlying_price=underlying_price,
            reason=reason,
            agent=agent,
        )
        
        if trade:
            logger.info(
                f"✅ [MultiLeg] {ml_pos.trade_type.upper()} closed:\n"
                f"   Combined P&L: ${trade.combined_pnl:.2f} ({trade.combined_pnl_pct:.1f}%)\n"
                f"   Net Premium: ${trade.net_premium:.2f}\n"
                f"   Duration: {trade.duration_minutes:.1f} minutes"
            )
        
        return trade

    def _execute_multi_leg_trade(
        self,
        intent: FinalTradeIntent,
        symbol: str,
        underlying_price: float,
        regime_at_entry: Optional[str] = None,
        vol_bucket_at_entry: Optional[str] = None,
    ) -> OptionsExecutionResult:
        """
        Execute multi-leg options trades (straddles and strangles).
        
        Features:
        - Two orders per leg (call + put)
        - Fill tracking for each leg
        - Combined P&L calculation
        - Credit/debit verification
        
        For STRADDLE: Sell/buy ATM call + ATM put at same strike
        For STRANGLE: Buy/sell OTM call + OTM put at different strikes
        """
        from core.portfolio.options_manager import LegFill, MultiLegPosition
        from core.live.types import OrderSide, OrderType
        
        metadata = intent.metadata or {}
        trade_type = intent.option_type  # "straddle" or "strangle"
        
        # Determine direction from intent
        # Theta Harvester sells (SHORT), Gamma Scalper buys (LONG)
        direction = "short" if intent.position_delta < 0 else "long"
        size = int(abs(intent.position_delta))  # Number of contracts
        
        # Get option symbols and strikes from metadata
        call_symbol = metadata.get("call_symbol", "")
        put_symbol = metadata.get("put_symbol", "")
        expiration_str = metadata.get("expiration", "")
        
        if not call_symbol or not put_symbol:
            return OptionsExecutionResult(
                success=False,
                reason=f"Missing option symbols for {trade_type}: call={call_symbol}, put={put_symbol}",
            )
        
        # Parse expiration
        try:
            if expiration_str:
                # Try parsing expiration string (format may vary)
                if "T" in expiration_str:
                    expiration = datetime.fromisoformat(expiration_str.replace("Z", "+00:00"))
                else:
                    # Assume YYYY-MM-DD format
                    expiration = datetime.strptime(expiration_str, "%Y-%m-%d")
            else:
                # Default to 0DTE if not specified
                expiration = datetime.now().replace(hour=16, minute=0, second=0, microsecond=0)
        except Exception as e:
            logger.warning(f"Could not parse expiration {expiration_str}, using default: {e}")
            expiration = datetime.now().replace(hour=16, minute=0, second=0, microsecond=0)
        
        # Get strikes
        if trade_type == "straddle":
            strike = float(metadata.get("strike", underlying_price))
            call_strike = strike
            put_strike = strike
        elif trade_type == "strangle":
            call_strike = float(metadata.get("call_strike", underlying_price * 1.05))
            put_strike = float(metadata.get("put_strike", underlying_price * 0.95))
        else:
            return OptionsExecutionResult(
                success=False,
                reason=f"Unknown multi-leg trade type: {trade_type}",
            )
        
        # Get quotes for pricing
        call_quote = None
        put_quote = None
        call_greeks = None
        put_greeks = None
        
        if self.options_data_feed:
            call_quote = self.options_data_feed.get_option_quote(call_symbol)
            put_quote = self.options_data_feed.get_option_quote(put_symbol)
            call_greeks = self.options_data_feed.get_option_greeks(call_symbol)
            put_greeks = self.options_data_feed.get_option_greeks(put_symbol)
        
        # Determine entry prices
        # For SHORT: use bid (selling premium)
        # For LONG: use ask (buying premium)
        if direction == "short":
            call_entry_price = float(call_quote.get("bid", 0)) if call_quote else 0.0
            put_entry_price = float(put_quote.get("bid", 0)) if put_quote else 0.0
        else:
            call_entry_price = float(call_quote.get("ask", 0)) if call_quote else 0.0
            put_entry_price = float(put_quote.get("ask", 0)) if put_quote else 0.0
        
        if call_entry_price <= 0 or put_entry_price <= 0:
            logger.warning(f"⚠️ [MultiLeg] Invalid prices: call=${call_entry_price:.2f}, put=${put_entry_price:.2f}")
            # Fallback to synthetic pricing
            call_entry_price = self.pricer.calculate_option_price(
                underlying_price=underlying_price,
                strike=call_strike,
                time_to_expiry=(expiration - datetime.now()).total_seconds() / (365 * 24 * 3600),
                iv=self.default_iv,
                option_type="call",
                risk_free_rate=self.default_risk_free_rate,
            )
            put_entry_price = self.pricer.calculate_option_price(
                underlying_price=underlying_price,
                strike=put_strike,
                time_to_expiry=(expiration - datetime.now()).total_seconds() / (365 * 24 * 3600),
                iv=self.default_iv,
                option_type="put",
                risk_free_rate=self.default_risk_free_rate,
            )
        
        # Get Greeks
        call_delta = float(call_greeks.get("delta", 0.0)) if call_greeks else 0.0
        call_theta = float(call_greeks.get("theta", 0.0)) if call_greeks else 0.0
        call_iv = float(call_greeks.get("implied_volatility", self.default_iv)) if call_greeks else self.default_iv
        
        put_delta = float(put_greeks.get("delta", 0.0)) if put_greeks else 0.0
        put_theta = float(put_greeks.get("theta", 0.0)) if put_greeks else 0.0
        put_iv = float(put_greeks.get("implied_volatility", self.default_iv)) if put_greeks else self.default_iv
        
        # Calculate expected net premium
        contract_multiplier = 100.0
        call_cost = call_entry_price * size * contract_multiplier
        put_cost = put_entry_price * size * contract_multiplier
        
        if direction == "short":
            expected_credit = call_cost + put_cost
            expected_debit = 0.0
        else:
            expected_debit = call_cost + put_cost
            expected_credit = 0.0
        
        # Verify against metadata if available
        if "total_credit" in metadata:
            expected_credit_from_metadata = float(metadata["total_credit"]) * size * contract_multiplier
            if abs(expected_credit - expected_credit_from_metadata) > expected_credit * 0.1:  # 10% tolerance
                logger.warning(
                    f"⚠️ [MultiLeg] Credit mismatch: calculated=${expected_credit:.2f}, "
                    f"expected=${expected_credit_from_metadata:.2f}"
                )
        
        if "total_debit" in metadata:
            expected_debit_from_metadata = float(metadata["total_debit"]) * size * contract_multiplier
            if abs(expected_debit - expected_debit_from_metadata) > expected_debit * 0.1:  # 10% tolerance
                logger.warning(
                    f"⚠️ [MultiLeg] Debit mismatch: calculated=${expected_debit:.2f}, "
                    f"expected=${expected_debit_from_metadata:.2f}"
                )
        
        # Generate unique multi-leg ID
        multi_leg_id = f"{symbol}_{trade_type.upper()}_{direction}_{int(call_strike)}_{int(put_strike)}_{expiration.strftime('%Y%m%d')}"
        
        logger.info(
            f"🔵 [MultiLeg] Executing {direction.upper()} {trade_type.upper()} {size}x: "
            f"CALL ${call_strike:.2f} @ ${call_entry_price:.2f} + PUT ${put_strike:.2f} @ ${put_entry_price:.2f}"
        )
        logger.info(
            f"🔵 [MultiLeg] Expected {'credit' if direction == 'short' else 'debit'}: "
            f"${expected_credit if direction == 'short' else expected_debit:.2f}"
        )
        
        # ============================================================
        # EXECUTE TWO ORDERS (ONE PER LEG)
        # ============================================================
        call_fill = None
        put_fill = None
        
        # Check if this is simulation-only (e.g., Alpaca paper trading limitation)
        is_sim_only = metadata.get("sim_only", False)
        
        if self.options_broker_client and not is_sim_only:
            # REAL ALPACA ORDER EXECUTION
            try:
                from core.live.types import OrderSide, OrderType
                
                side = OrderSide.SELL if direction == "short" else OrderSide.BUY
                
                # Submit call order
                logger.info(f"📤 [MultiLeg] Submitting CALL order: {side.value} {size} contracts of {call_symbol}")
                call_order = self.options_broker_client.submit_options_order(
                    option_symbol=call_symbol,
                    side=side,
                    quantity=size,
                    order_type=OrderType.LIMIT,
                    limit_price=call_entry_price,
                )
                
                # Submit put order
                logger.info(f"📤 [MultiLeg] Submitting PUT order: {side.value} {size} contracts of {put_symbol}")
                put_order = self.options_broker_client.submit_options_order(
                    option_symbol=put_symbol,
                    side=side,
                    quantity=size,
                    order_type=OrderType.LIMIT,
                    limit_price=put_entry_price,
                )
                
                # Track fills
                call_fill = LegFill(
                    leg_type="call",
                    option_symbol=call_symbol,
                    strike=call_strike,
                    quantity=call_order.filled_quantity if call_order.filled_quantity > 0 else size,
                    fill_price=call_order.filled_price if call_order.filled_price > 0 else call_entry_price,
                    fill_time=datetime.now(),
                    order_id=call_order.order_id,
                    status=call_order.status.value if hasattr(call_order.status, 'value') else str(call_order.status),
                )
                
                put_fill = LegFill(
                    leg_type="put",
                    option_symbol=put_symbol,
                    strike=put_strike,
                    quantity=put_order.filled_quantity if put_order.filled_quantity > 0 else size,
                    fill_price=put_order.filled_price if put_order.filled_price > 0 else put_entry_price,
                    fill_time=datetime.now(),
                    order_id=put_order.order_id,
                    status=put_order.status.value if hasattr(put_order.status, 'value') else str(put_order.status),
                )
                
                logger.info(
                    f"✅ [MultiLeg] CALL fill: {call_fill.quantity} @ ${call_fill.fill_price:.2f} "
                    f"(status: {call_fill.status})"
                )
                logger.info(
                    f"✅ [MultiLeg] PUT fill: {put_fill.quantity} @ ${put_fill.fill_price:.2f} "
                    f"(status: {put_fill.status})"
                )
                
                # Verify credit/debit matches
                actual_call_cost = call_fill.total_cost
                actual_put_cost = put_fill.total_cost
                actual_net = actual_call_cost + actual_put_cost
                
                if direction == "short":
                    actual_credit = actual_net
                    logger.info(
                        f"✅ [MultiLeg] Actual credit: ${actual_credit:.2f} "
                        f"(expected: ${expected_credit:.2f}, diff: ${actual_credit - expected_credit:.2f})"
                    )
                else:
                    actual_debit = actual_net
                    logger.info(
                        f"✅ [MultiLeg] Actual debit: ${actual_debit:.2f} "
                        f"(expected: ${expected_debit:.2f}, diff: ${actual_debit - expected_debit:.2f})"
                    )
                
            except Exception as e:
                logger.error(f"❌ [MultiLeg] Failed to submit real orders: {e}", exc_info=True)
                # Fall through to synthetic execution
                logger.info("⚠️ [MultiLeg] Falling back to synthetic execution")
        
        # If no real fills, create synthetic fills
        if call_fill is None or put_fill is None:
            call_fill = LegFill(
                leg_type="call",
                option_symbol=call_symbol,
                strike=call_strike,
                quantity=size,
                fill_price=call_entry_price,
                fill_time=datetime.now(),
                status="filled",
            )
            
            put_fill = LegFill(
                leg_type="put",
                option_symbol=put_symbol,
                strike=put_strike,
                quantity=size,
                fill_price=put_entry_price,
                fill_time=datetime.now(),
                status="filled",
            )
            
            logger.info(f"📊 [MultiLeg] Using synthetic fills (no real broker client)")
        
        # ============================================================
        # CREATE MULTI-LEG POSITION
        # ============================================================
        ml_pos = self.options_portfolio.add_multi_leg_position(
            symbol=symbol,
            trade_type=trade_type,
            direction=direction,
            multi_leg_id=multi_leg_id,
            call_option_symbol=call_symbol,
            call_strike=call_strike,
            call_quantity=size,
            call_entry_price=call_fill.fill_price,
            call_delta=call_delta,
            call_theta=call_theta,
            call_iv=call_iv,
            put_option_symbol=put_symbol,
            put_strike=put_strike,
            put_quantity=size,
            put_entry_price=put_fill.fill_price,
            put_delta=put_delta,
            put_theta=put_theta,
            put_iv=put_iv,
            expiration=expiration,
            entry_time=datetime.now(),
            underlying_price=underlying_price,
            call_fill=call_fill,
            put_fill=put_fill,
            regime_at_entry=regime_at_entry,
            vol_bucket_at_entry=vol_bucket_at_entry,
        )
        
        # Update fills in position
        self.options_portfolio.update_multi_leg_fill(multi_leg_id, "call", call_fill)
        self.options_portfolio.update_multi_leg_fill(multi_leg_id, "put", put_fill)
        
        logger.info(
            f"✅ [MultiLeg] {trade_type.upper()} position created: {multi_leg_id}\n"
            f"   CALL: {size}x @ ${call_fill.fill_price:.2f} (fill: {call_fill.status})\n"
            f"   PUT: {size}x @ ${put_fill.fill_price:.2f} (fill: {put_fill.status})\n"
            f"   Net {'credit' if direction == 'short' else 'debit'}: "
            f"${ml_pos.net_premium:.2f}\n"
            f"   Both legs filled: {ml_pos.both_legs_filled}"
        )
        
        return OptionsExecutionResult(
            success=True,
            reason=(
                f"{direction.upper()} {trade_type.upper()} {size}x executed: "
                f"CALL @ ${call_fill.fill_price:.2f} + PUT @ ${put_fill.fill_price:.2f}, "
                f"net {'credit' if direction == 'short' else 'debit'}=${ml_pos.net_premium:.2f}"
            ),
            option_symbol=multi_leg_id,
        )
    
    def _generate_option_symbol(
        self,
        symbol: str,
        option_type: str,
        strike: float,
        expiration: datetime,
        moneyness: str,
    ) -> str:
        """Generate a synthetic option symbol identifier."""
        # Format: SYMBOL_TYPE_STRIKE_EXP_MONEYNESS
        # e.g., "QQQ_CALL_600_20241124_ATM"
        exp_str = expiration.strftime("%Y%m%d")
        type_str = option_type.upper()
        strike_str = f"{int(strike)}"
        return f"{symbol}_{type_str}_{strike_str}_{exp_str}_{moneyness.upper()}"

