from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from core.live.types import Account, Fill, Order, OrderSide, OrderStatus, OrderType, Position, TimeInForce


class BaseBrokerClient(ABC):
    """Abstract base class for broker clients."""

    @abstractmethod
    def get_account(self) -> Account:
        """Get account information."""
        pass

    @abstractmethod
    def get_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """Get current positions."""
        pass

    @abstractmethod
    def submit_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        order_type: OrderType,
        time_in_force: TimeInForce = TimeInForce.DAY,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
    ) -> Order:
        """Submit an order."""
        pass

    @abstractmethod
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get open orders."""
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        pass

    @abstractmethod
    def get_recent_fills(self, symbol: Optional[str] = None, limit: int = 50) -> List[Fill]:
        """Get recent order fills."""
        pass


class AlpacaBrokerClient(BaseBrokerClient):
    """Alpaca broker client implementation using alpaca-py."""

    def __init__(self, api_key: str, api_secret: str, base_url: str = "https://paper-api.alpaca.markets"):
        """
        Initialize Alpaca broker client.
        
        Args:
            api_key: Alpaca API key
            api_secret: Alpaca API secret
            base_url: Alpaca API base URL (default: paper trading)
        """
        import logging
        self.logger = logging.getLogger(__name__)
        
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self.is_paper = "paper-api" in base_url
        
        try:
            from alpaca.trading.client import TradingClient
            from alpaca.data.historical import StockHistoricalDataClient
            from alpaca.data.requests import StockBarsRequest
            from alpaca.data.timeframe import TimeFrame
            
            # Initialize Alpaca clients
            self.trading_client = TradingClient(
                api_key=api_key,
                secret_key=api_secret,
                paper=self.is_paper
            )
            self.data_client = StockHistoricalDataClient(
                api_key=api_key,
                secret_key=api_secret
            )
            self._connected = True
            self.logger.info(f"Alpaca client initialized (paper={self.is_paper})")
        except ImportError:
            raise ImportError("alpaca-py not installed. Run: pip install alpaca-py")
        except Exception as e:
            self.logger.error(f"Failed to initialize Alpaca client: {e}")
            raise

    def get_account(self) -> Account:
        """Get Alpaca account information."""
        try:
            account = self.trading_client.get_account()
            return Account(
                cash=float(account.cash),
                equity=float(account.equity),
                buying_power=float(account.buying_power),
                portfolio_value=float(account.portfolio_value),
            )
        except Exception as e:
            self.logger.error(f"Error getting Alpaca account: {e}")
            # Return default on error
        return Account(
            cash=100000.0,
            equity=100000.0,
            buying_power=200000.0,
            portfolio_value=100000.0,
        )

    def get_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """Get Alpaca positions."""
        try:
            positions = self.trading_client.get_all_positions()
            result = []
            for pos in positions:
                if symbol and pos.symbol != symbol:
                    continue
                result.append(
                    Position(
                        symbol=pos.symbol,
                        quantity=float(pos.qty),
                        avg_entry_price=float(pos.avg_entry_price),
                        current_price=float(pos.current_price),
                        market_value=float(pos.market_value),
                        unrealized_pnl=float(pos.unrealized_pl),
                    )
                )
            return result
        except Exception as e:
            self.logger.error(f"Error getting Alpaca positions: {e}")
        return []

    def submit_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        order_type: OrderType,
        time_in_force: TimeInForce = TimeInForce.DAY,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
    ) -> Order:
        """Submit order to Alpaca (supports both stocks and crypto)."""
        from datetime import datetime
        from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, StopOrderRequest
        
        try:
            # Check if this is a crypto symbol
            is_crypto = "/USD" in symbol.upper() or any(crypto in symbol.upper() for crypto in ["BTC", "ETH", "SOL", "AVAX", "MATIC", "LINK", "UNI", "AAVE", "ALGO", "DOGE"])
            
            # Convert our order types to Alpaca types
            qty = abs(quantity)
            order_side = "buy" if side == OrderSide.BUY else "sell"
            
            # Map time in force
            tif_map = {
                TimeInForce.DAY: "day",
                TimeInForce.GTC: "gtc",
                TimeInForce.IOC: "ioc",
                TimeInForce.FOK: "fok",
            }
            alpaca_tif = tif_map.get(time_in_force, "day")
            
            # Create order request based on type
            if order_type == OrderType.MARKET:
                order_request = MarketOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=order_side,
                    time_in_force=alpaca_tif,
                )
            elif order_type == OrderType.LIMIT:
                if limit_price is None:
                    raise ValueError("Limit price required for limit orders")
                order_request = LimitOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=order_side,
                    time_in_force=alpaca_tif,
                    limit_price=limit_price,
                )
            elif order_type == OrderType.STOP:
                if stop_price is None:
                    raise ValueError("Stop price required for stop orders")
                order_request = StopOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=order_side,
                    time_in_force=alpaca_tif,
                    stop_price=stop_price,
                )
            else:
                raise ValueError(f"Unsupported order type: {order_type}")
            
            # Submit order
            order = self.trading_client.submit_order(order_request)
            
            # Convert to our Order type
            status_map = {
                "new": OrderStatus.SUBMITTED,
                "accepted": OrderStatus.SUBMITTED,
                "pending_new": OrderStatus.SUBMITTED,
                "filled": OrderStatus.FILLED,
                "partially_filled": OrderStatus.PARTIALLY_FILLED,
                "canceled": OrderStatus.CANCELLED,
                "expired": OrderStatus.CANCELLED,
                "rejected": OrderStatus.REJECTED,
            }
            
            return Order(
                order_id=str(order.id),
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type=order_type,
            time_in_force=time_in_force,
                status=status_map.get(order.status.lower(), OrderStatus.SUBMITTED),
            limit_price=limit_price,
            stop_price=stop_price,
            submitted_at=datetime.now(),
        )
        except Exception as e:
            self.logger.error(f"Error submitting Alpaca order: {e}")
            # Return failed order
            return Order(
                order_id="ERROR",
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type=order_type,
                time_in_force=time_in_force,
                status=OrderStatus.REJECTED,
                submitted_at=datetime.now(),
            )

    def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get open orders from Alpaca."""
        from datetime import datetime
        try:
            orders = self.trading_client.get_orders(status="open")
            result = []
            for order in orders:
                if symbol and order.symbol != symbol:
                    continue
                
                # Convert Alpaca order to our Order type
                side = OrderSide.BUY if order.side == "buy" else OrderSide.SELL
                
                order_type = OrderType.MARKET
                if hasattr(order, "order_type"):
                    if order.order_type == "limit":
                        order_type = OrderType.LIMIT
                    elif order.order_type == "stop":
                        order_type = OrderType.STOP
                
                tif_map = {
                    "day": TimeInForce.DAY,
                    "gtc": TimeInForce.GTC,
                    "ioc": TimeInForce.IOC,
                    "fok": TimeInForce.FOK,
                }
                time_in_force = tif_map.get(order.time_in_force.lower(), TimeInForce.DAY)
                
                status_map = {
                    "new": OrderStatus.SUBMITTED,
                    "accepted": OrderStatus.SUBMITTED,
                    "pending_new": OrderStatus.SUBMITTED,
                }
                
                result.append(
                    Order(
                        order_id=str(order.id),
                        symbol=order.symbol,
                        side=side,
                        quantity=float(order.qty),
                        order_type=order_type,
                        time_in_force=time_in_force,
                        status=status_map.get(order.status.lower(), OrderStatus.SUBMITTED),
                        limit_price=float(order.limit_price) if hasattr(order, "limit_price") and order.limit_price else None,
                        stop_price=float(order.stop_price) if hasattr(order, "stop_price") and order.stop_price else None,
                        submitted_at=order.submitted_at if hasattr(order, "submitted_at") else datetime.now(),
                    )
                )
            return result
        except Exception as e:
            self.logger.error(f"Error getting Alpaca open orders: {e}")
        return []

    def cancel_order(self, order_id: str) -> bool:
        """Cancel order on Alpaca."""
        try:
            self.trading_client.cancel_order_by_id(order_id)
            return True
        except Exception as e:
            self.logger.error(f"Error canceling Alpaca order {order_id}: {e}")
            return False

    def get_recent_fills(self, symbol: Optional[str] = None, limit: int = 50) -> List[Fill]:
        """Get recent fills from Alpaca."""
        from datetime import datetime
        try:
            # Get filled orders
            orders = self.trading_client.get_orders(status="closed", limit=limit)
            fills = []
            for order in orders:
                if symbol and order.symbol != symbol:
                    continue
                if order.status != "filled":
                    continue
                
                # Get execution details
                side = OrderSide.BUY if order.side == "buy" else OrderSide.SELL
                
                # Alpaca fills are typically in the order's filled_avg_price
                fill_price = float(order.filled_avg_price) if hasattr(order, "filled_avg_price") else 0.0
                fill_qty = float(order.filled_qty) if hasattr(order, "filled_qty") else float(order.qty)
                
                fills.append(
                    Fill(
                        order_id=str(order.id),
                        symbol=order.symbol,
                        side=side,
                        quantity=fill_qty,
                        price=fill_price,
                        timestamp=order.filled_at if hasattr(order, "filled_at") else datetime.now(),
                    )
                )
            return fills[:limit]
        except Exception as e:
            self.logger.error(f"Error getting Alpaca fills: {e}")
        return []


class PaperBrokerClient(BaseBrokerClient):
    """Paper trading broker client (for testing without real broker)."""

    def __init__(self, initial_cash: float = 100000.0):
        self.cash = initial_cash
        self.positions: dict[str, Position] = {}
        self.orders: dict[str, Order] = {}
        self.fills: List[Fill] = []

    def get_account(self) -> Account:
        """Get paper account."""
        portfolio_value = self.cash + sum(pos.market_value for pos in self.positions.values())
        return Account(
            cash=self.cash,
            equity=portfolio_value,
            buying_power=self.cash * 2.0,  # 2x margin for paper
            portfolio_value=portfolio_value,
        )

    def get_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """Get paper positions."""
        if symbol:
            return [self.positions[symbol]] if symbol in self.positions else []
        return list(self.positions.values())

    def submit_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        order_type: OrderType,
        time_in_force: TimeInForce = TimeInForce.DAY,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
    ) -> Order:
        """Submit paper order (immediately filled at limit_price or current price)."""
        from datetime import datetime
        from uuid import uuid4

        order_id = str(uuid4())
        fill_price = limit_price or 100.0  # Default price for paper trading

        # Create order
        order = Order(
            order_id=order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            time_in_force=time_in_force,
            status=OrderStatus.FILLED,
            filled_quantity=quantity,
            filled_price=fill_price,
            limit_price=limit_price,
            stop_price=stop_price,
            submitted_at=datetime.now(),
            filled_at=datetime.now(),
        )

        self.orders[order_id] = order

        # Update positions
        cost = quantity * fill_price
        if side == OrderSide.BUY:
            if symbol in self.positions:
                pos = self.positions[symbol]
                total_cost = (pos.quantity * pos.avg_entry_price) + cost
                total_qty = pos.quantity + quantity
                self.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=total_qty,
                    avg_entry_price=total_cost / total_qty,
                    current_price=fill_price,
                    market_value=total_qty * fill_price,
                    unrealized_pnl=(fill_price - total_cost / total_qty) * total_qty,
                )
            else:
                self.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=quantity,
                    avg_entry_price=fill_price,
                    current_price=fill_price,
                    market_value=quantity * fill_price,
                    unrealized_pnl=0.0,
                )
            self.cash -= cost
        else:  # SELL
            if symbol in self.positions:
                pos = self.positions[symbol]
                new_qty = pos.quantity - quantity
                if new_qty <= 0:
                    del self.positions[symbol]
                else:
                    self.positions[symbol] = Position(
                        symbol=symbol,
                        quantity=new_qty,
                        avg_entry_price=pos.avg_entry_price,
                        current_price=fill_price,
                        market_value=new_qty * fill_price,
                        unrealized_pnl=(fill_price - pos.avg_entry_price) * new_qty,
                    )
                self.cash += cost

        # Record fill
        fill = Fill(
            order_id=order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=fill_price,
            timestamp=datetime.now(),
        )
        self.fills.append(fill)

        return order

    def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get open paper orders."""
        open_orders = [o for o in self.orders.values() if o.status == OrderStatus.SUBMITTED]
        if symbol:
            open_orders = [o for o in open_orders if o.symbol == symbol]
        return open_orders

    def cancel_order(self, order_id: str) -> bool:
        """Cancel paper order."""
        if order_id in self.orders:
            self.orders[order_id].status = OrderStatus.CANCELLED
            return True
        return False

    def get_recent_fills(self, symbol: Optional[str] = None, limit: int = 50) -> List[Fill]:
        """Get recent paper fills."""
        fills = self.fills[-limit:] if len(self.fills) > limit else self.fills
        if symbol:
            fills = [f for f in fills if f.symbol == symbol]
        return fills

