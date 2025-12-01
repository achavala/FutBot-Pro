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
        
        For STRADDLE: Sell/buy ATM call + ATM put at same strike
        For STRANGLE: Buy/sell OTM call + OTM put at different strikes
        """
        metadata = intent.metadata or {}
        trade_type = intent.option_type  # "straddle" or "strangle"
        direction = getattr(intent, 'direction', 'long')  # "long" or "short" (default to long)
        size = int(abs(intent.position_delta))  # Number of contracts
        
        if trade_type == "straddle":
            strike = float(metadata.get("strike", underlying_price))
            call_symbol = metadata.get("call_symbol", "")
            put_symbol = metadata.get("put_symbol", "")
            expiration_str = metadata.get("expiration", "")
            
            logger.info(
                f"[EXECUTOR] {direction.upper()} STRADDLE {size}x @ ${strike:.2f}: "
                f"CALL {call_symbol} + PUT {put_symbol}"
            )
            
            # Execute both legs
            # For now, we'll create synthetic positions for both legs
            # In production, this would execute two separate orders
            
            # TODO: Implement actual straddle execution
            # This is a stub that logs the trade
            logger.info(
                f"[EXECUTOR] Straddle execution stub: {direction} {size} contracts "
                f"at strike ${strike:.2f}, expiration {expiration_str}"
            )
            
            return OptionsExecutionResult(
                success=True,
                reason=f"Straddle {direction} {size}x @ ${strike:.2f} (execution stub)",
                option_symbol=f"{symbol}_STRADDLE_{int(strike)}_{expiration_str}",
            )
        
        elif trade_type == "strangle":
            call_strike = float(metadata.get("call_strike", underlying_price * 1.05))
            put_strike = float(metadata.get("put_strike", underlying_price * 0.95))
            call_symbol = metadata.get("call_symbol", "")
            put_symbol = metadata.get("put_symbol", "")
            expiration_str = metadata.get("expiration", "")
            
            logger.info(
                f"[EXECUTOR] {direction.upper()} STRANGLE {size}x: "
                f"CALL ${call_strike:.2f} ({call_symbol}) + PUT ${put_strike:.2f} ({put_symbol})"
            )
            
            # Execute both legs
            # TODO: Implement actual strangle execution
            logger.info(
                f"[EXECUTOR] Strangle execution stub: {direction} {size} contracts "
                f"CALL @ ${call_strike:.2f} / PUT @ ${put_strike:.2f}, expiration {expiration_str}"
            )
            
            return OptionsExecutionResult(
                success=True,
                reason=(
                    f"Strangle {direction} {size}x: "
                    f"CALL ${call_strike:.2f} / PUT ${put_strike:.2f} (execution stub)"
                ),
                option_symbol=f"{symbol}_STRANGLE_{int(call_strike)}_{int(put_strike)}_{expiration_str}",
            )
        
        else:
            return OptionsExecutionResult(
                success=False,
                reason=f"Unknown multi-leg trade type: {trade_type}",
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

