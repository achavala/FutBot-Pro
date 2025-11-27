"""Options broker client for Alpaca options trading."""

from __future__ import annotations

import logging
from typing import List, Optional

from core.live.broker_client import AlpacaBrokerClient
from core.live.types import Account, Fill, Order, OrderSide, OrderType, Position

logger = logging.getLogger(__name__)


class OptionsBrokerClient(AlpacaBrokerClient):
    """Broker client for options trading via Alpaca."""
    
    def submit_options_order(
        self,
        option_symbol: str,
        side: OrderSide,
        quantity: int,  # Options contracts (not shares)
        order_type: OrderType = OrderType.MARKET,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "day",
    ) -> Order:
        """
        Submit an options order.
        
        Args:
            option_symbol: Full option symbol (e.g., "SPY251126P00673000")
            side: BUY or SELL
            quantity: Number of contracts (not shares)
            order_type: MARKET, LIMIT, etc.
            limit_price: Limit price (required for LIMIT orders)
            stop_price: Stop price (for STOP orders)
            time_in_force: "day", "gtc", "ioc", "fok"
        
        Returns:
            Order object
        """
        try:
            from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, StopOrderRequest
            from alpaca.trading.enums import OrderSide as AlpacaOrderSide, TimeInForce
            
            # Convert to Alpaca types
            alpaca_side = AlpacaOrderSide.BUY if side == OrderSide.BUY else AlpacaOrderSide.SELL
            
            time_in_force_map = {
                "day": TimeInForce.DAY,
                "gtc": TimeInForce.GTC,
                "ioc": TimeInForce.IOC,
                "fok": TimeInForce.FOK,
            }
            alpaca_tif = time_in_force_map.get(time_in_force.lower(), TimeInForce.DAY)
            
            # Create order request
            if order_type == OrderType.MARKET:
                order_request = MarketOrderRequest(
                    symbol=option_symbol,
                    qty=quantity,  # Number of contracts
                    side=alpaca_side,
                    time_in_force=alpaca_tif,
                )
            elif order_type == OrderType.LIMIT:
                if not limit_price:
                    raise ValueError("limit_price required for LIMIT orders")
                order_request = LimitOrderRequest(
                    symbol=option_symbol,
                    qty=quantity,
                    side=alpaca_side,
                    limit_price=limit_price,
                    time_in_force=alpaca_tif,
                )
            elif order_type == OrderType.STOP:
                if not stop_price:
                    raise ValueError("stop_price required for STOP orders")
                order_request = StopOrderRequest(
                    symbol=option_symbol,
                    qty=quantity,
                    side=alpaca_side,
                    stop_price=stop_price,
                    time_in_force=alpaca_tif,
                )
            else:
                raise ValueError(f"Unsupported order type: {order_type}")
            
            # Submit order
            order = self.trading_client.submit_order(order_request)
            
            # Convert to our Order type
            return Order(
                order_id=order.id,
                symbol=option_symbol,
                side=side,
                quantity=float(order.qty),
                order_type=order_type,
                status=order.status.value,
                filled_quantity=float(order.filled_qty) if order.filled_qty else 0.0,
                filled_price=float(order.filled_avg_price) if order.filled_avg_price else 0.0,
            )
        except Exception as e:
            logger.error(f"Failed to submit options order: {e}")
            raise
    
    def get_options_positions(self, underlying_symbol: Optional[str] = None) -> List[Position]:
        """
        Get open options positions.
        
        Args:
            underlying_symbol: Filter by underlying (e.g., "SPY") or None for all
        
        Returns:
            List of Position objects for options
        """
        try:
            positions = self.trading_client.get_all_positions()
            
            options_positions = []
            for pos in positions:
                # Check if it's an options position (options symbols are longer)
                # Alpaca options symbols typically have format like "SPY251126P00673000"
                if underlying_symbol:
                    if not pos.symbol.startswith(underlying_symbol):
                        continue
                
                options_positions.append(
                    Position(
                        symbol=pos.symbol,
                        quantity=float(pos.qty),
                        avg_entry_price=float(pos.avg_entry_price),
                        current_price=float(pos.current_price) if pos.current_price else 0.0,
                        market_value=float(pos.market_value) if pos.market_value else 0.0,
                    )
                )
            
            return options_positions
        except Exception as e:
            logger.error(f"Failed to get options positions: {e}")
            return []
    
    def close_options_position(self, option_symbol: str, quantity: int) -> bool:
        """
        Close an options position.
        
        Args:
            option_symbol: Full option symbol
            quantity: Number of contracts to close
        
        Returns:
            True if successful
        """
        try:
            # Get current position to determine side
            positions = self.get_options_positions()
            position = next((p for p in positions if p.symbol == option_symbol), None)
            
            if not position:
                logger.warning(f"No position found for {option_symbol}")
                return False
            
            # Determine side (opposite of current position)
            side = OrderSide.SELL if position.quantity > 0 else OrderSide.BUY
            
            # Submit closing order
            order = self.submit_options_order(
                option_symbol=option_symbol,
                side=side,
                quantity=abs(quantity),
                order_type=OrderType.MARKET,
            )
            
            return order.status in ["filled", "partially_filled"]
        except Exception as e:
            logger.error(f"Failed to close options position: {e}")
            return False

