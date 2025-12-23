"""Interactive Brokers broker client implementation using ib_insync."""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import List, Optional

from ib_insync import IB, MarketOrder, LimitOrder, StopOrder, Order as IBOrder, Stock, util

from core.live.broker_client import BaseBrokerClient
from core.live.types import Account, Fill, Order, OrderSide, OrderStatus, OrderType, Position, TimeInForce

logger = logging.getLogger(__name__)

# Thread pool for running IB operations to avoid event loop conflicts
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ibkr")
_loop_started = False
_loop_lock = threading.Lock()

def _ensure_loop():
    """Ensure ib_insync event loop is running in a separate thread."""
    global _loop_started
    with _loop_lock:
        if not _loop_started:
            def start_loop():
                try:
                    util.startLoop()
                except RuntimeError:
                    pass  # Loop already running
            
            # Start loop in executor thread
            _executor.submit(start_loop)
            import time
            time.sleep(0.1)  # Give loop time to start
            _loop_started = True

# Lazy initialization - don't start loop at import time
# This avoids conflict with uvicorn's uvloop
# Loop will be started when IBKRBrokerClient is actually instantiated
IBKR_LOOP_STARTED = False

def _ensure_ibkr_loop():
    """Ensure IBKR event loop is started (lazy initialization)."""
    global IBKR_LOOP_STARTED
    if not IBKR_LOOP_STARTED:
        try:
            from ib_insync import util
            # Only start loop if not already started and not using uvloop
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                # If using uvloop, we can't patch it - skip IBKR loop start
                if 'uvloop' in str(type(loop)):
                    # Skip IBKR loop initialization when using uvloop
                    return False
            except RuntimeError:
                pass
            
            if not hasattr(util, '_loop_started'):
                util.startLoop()
                util._loop_started = True
                IBKR_LOOP_STARTED = True
                return True
        except ImportError:
            pass
        except Exception as e:
            # If loop patching fails (e.g., with uvloop), continue without it
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Could not start IBKR loop (may be using uvloop): {e}")
            return False
    return IBKR_LOOP_STARTED


class IBKRBrokerClient(BaseBrokerClient):
    """Interactive Brokers client using ib_insync with lazy loop initialization."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 7497,  # 7497 for paper, 7496 for live
        client_id: Optional[int] = None,
        account_id: Optional[str] = None,
    ):
        """
        Initialize IBKR client.

        Args:
            host: IB Gateway/TWS host (default: localhost)
            port: IB Gateway/TWS port (7497 for paper, 7496 for live)
            client_id: Client ID for connection
            account_id: Specific account ID (optional)
        """
        # Lazy initialize IBKR loop only when actually creating client
        _ensure_ibkr_loop()
        self.host = host
        self.port = port
        # Use random client ID if not provided to avoid conflicts
        if client_id is None:
            import random
            self.client_id = random.randint(100, 9999)  # Use higher range to avoid conflicts
        else:
            self.client_id = client_id
        self.account_id = account_id
        self.ib = None  # Will be created in thread
        self._connected = False
        self._connection_lock = threading.Lock()

    def connect(self) -> bool:
        """Connect to IB Gateway or TWS."""
        with self._connection_lock:
            if self._connected:
                return True
            
            try:
                # Run connection in executor thread with its own event loop
                def _connect():
                    try:
                        # Start event loop in this thread (if not already running)
                        try:
                            util.startLoop()
                        except RuntimeError:
                            pass  # Loop already running
                        
                        # Create IB instance in this thread (after loop is started)
                        ib = IB()
                        
                        # Disconnect first if already connected (cleanup)
                        try:
                            if ib.isConnected():
                                ib.disconnect()
                        except:
                            pass
                        
                        # Connect with timeout - this will use the thread's event loop
                        ib.connect(self.host, self.port, clientId=self.client_id, timeout=15)
                        
                        # Verify connection
                        if not ib.isConnected():
                            logger.error("Connection completed but IB reports not connected")
                            return False
                        
                        # Store IB instance
                        self.ib = ib
                        
                        # If no account specified, use the first one
                        if not self.account_id and ib.managedAccounts():
                            self.account_id = ib.managedAccounts()[0]
                            logger.info(f"Using account: {self.account_id}")
                        
                        return True
                    except Exception as e:
                        logger.error(f"Connection error in thread: {type(e).__name__}: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                        return False
                
                # Run in thread pool
                future = _executor.submit(_connect)
                result = future.result(timeout=20)
                
                if result:
                    self._connected = True
                    logger.info(f"Connected to IBKR at {self.host}:{self.port}")
                    return True
                else:
                    return False
                    
            except Exception as e:
                logger.error(f"Failed to connect to IBKR: {e}")
                self._connected = False
                return False

    def disconnect(self):
        """Disconnect from IB Gateway or TWS."""
        if self._connected and self.ib:
            try:
                self.ib.disconnect()
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            self._connected = False
            self.ib = None
            logger.info("Disconnected from IBKR")

    def _ensure_connected(self):
        """Ensure connection is active."""
        if not self._connected or self.ib is None:
            logger.warning("IBKR connection lost. Attempting to reconnect...")
            if self.connect():
                return
            raise RuntimeError("Not connected to IBKR. Call connect() first.")
        
        # Double check actual connection state
        if not self.ib.isConnected():
             logger.warning("IBKR socket disconnected. Attempting to reconnect...")
             self.disconnect()
             if self.connect():
                 return
             raise RuntimeError("IBKR socket disconnected")
    
    def _run_in_thread(self, func):
        """Run a function in the executor thread."""
        future = _executor.submit(func)
        return future.result(timeout=10)
    
    def get_account(self) -> Account:
        """Get IBKR account information."""
        self._ensure_connected()

        try:
            # Get account values (run in thread to avoid event loop issues)
            def _get_account():
                return self.ib.accountValues(self.account_id)
            
            account_values = self._run_in_thread(_get_account)

            cash = 0.0
            equity = 0.0
            buying_power = 0.0

            for av in account_values:
                if av.tag == "CashBalance" and av.currency == "USD":
                    cash = float(av.value)
                elif av.tag == "NetLiquidation" and av.currency == "USD":
                    equity = float(av.value)
                elif av.tag == "BuyingPower" and av.currency == "USD":
                    buying_power = float(av.value)

            return Account(
                cash=cash,
                equity=equity,
                buying_power=buying_power,
                portfolio_value=equity,
            )
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            # Return default values on error
            return Account(
                cash=100000.0,
                equity=100000.0,
                buying_power=200000.0,
                portfolio_value=100000.0,
            )

    def get_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """Get current IBKR positions."""
        self._ensure_connected()

        try:
            def _get_positions():
                return list(self.ib.positions(self.account_id))
            
            ib_positions = self._run_in_thread(_get_positions)
            positions = []
            for pos in ib_positions:
                # Filter by symbol if specified
                if symbol and pos.contract.symbol != symbol:
                    continue

                # Get current market price (run in thread)
                def _get_price():
                    ticker = self.ib.reqTicker(pos.contract)
                    return ticker.marketPrice() if ticker.marketPrice() > 0 else pos.avgCost
                
                current_price = self._run_in_thread(_get_price)

                quantity = pos.position
                avg_price = pos.avgCost
                market_value = quantity * current_price
                unrealized_pnl = (current_price - avg_price) * quantity

                positions.append(
                    Position(
                        symbol=pos.contract.symbol,
                        quantity=quantity,
                        avg_entry_price=avg_price,
                        current_price=current_price,
                        market_value=market_value,
                        unrealized_pnl=unrealized_pnl,
                    )
                )

            return positions
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
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
        current_price: Optional[float] = None,  # Ignored for IBKR (uses broker prices)
    ) -> Order:
        """Submit order to IBKR."""
        self._ensure_connected()

        try:
            # Create contract
            contract = Stock(symbol, "SMART", "USD")

            # Create order based on type
            action = "BUY" if side == OrderSide.BUY else "SELL"

            if order_type == OrderType.MARKET:
                ib_order = MarketOrder(action, quantity)
            elif order_type == OrderType.LIMIT:
                if limit_price is None:
                    raise ValueError("Limit price required for limit orders")
                ib_order = LimitOrder(action, quantity, limit_price)
            elif order_type == OrderType.STOP:
                if stop_price is None:
                    raise ValueError("Stop price required for stop orders")
                ib_order = StopOrder(action, quantity, stop_price)
            else:
                raise ValueError(f"Unsupported order type: {order_type}")

            # Set time in force
            if time_in_force == TimeInForce.DAY:
                ib_order.tif = "DAY"
            elif time_in_force == TimeInForce.GTC:
                ib_order.tif = "GTC"
            elif time_in_force == TimeInForce.IOC:
                ib_order.tif = "IOC"
            elif time_in_force == TimeInForce.FOK:
                ib_order.tif = "FOK"

            # Place order
            trade = self.ib.placeOrder(contract, ib_order)
            self.ib.sleep(0.1)  # Give time for order to be acknowledged

            # Convert to our Order type
            order = Order(
                order_id=str(trade.order.orderId),
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type=order_type,
                time_in_force=time_in_force,
                status=self._convert_order_status(trade.orderStatus.status),
                limit_price=limit_price,
                stop_price=stop_price,
                submitted_at=datetime.now(),
            )

            logger.info(f"Submitted order: {order.order_id} - {action} {quantity} {symbol}")
            return order

        except Exception as e:
            logger.error(f"Error submitting order: {e}")
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
        """Get open orders from IBKR."""
        self._ensure_connected()

        try:
            orders = []
            for trade in self.ib.openTrades():
                # Filter by symbol if specified
                if symbol and trade.contract.symbol != symbol:
                    continue

                order = self._convert_trade_to_order(trade)
                orders.append(order)

            return orders
        except Exception as e:
            logger.error(f"Error getting open orders: {e}")
            return []

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order on IBKR."""
        self._ensure_connected()

        try:
            # Find the trade by order ID
            for trade in self.ib.openTrades():
                if str(trade.order.orderId) == order_id:
                    self.ib.cancelOrder(trade.order)
                    logger.info(f"Cancelled order: {order_id}")
                    return True

            logger.warning(f"Order not found: {order_id}")
            return False
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False

    def get_recent_fills(self, symbol: Optional[str] = None, limit: int = 50) -> List[Fill]:
        """Get recent fills from IBKR."""
        self._ensure_connected()

        try:
            fills = []
            for fill in self.ib.fills()[-limit:]:
                # Filter by symbol if specified
                if symbol and fill.contract.symbol != symbol:
                    continue

                side = OrderSide.BUY if fill.execution.side == "BOT" else OrderSide.SELL

                fills.append(
                    Fill(
                        order_id=str(fill.execution.orderId),
                        symbol=fill.contract.symbol,
                        side=side,
                        quantity=fill.execution.shares,
                        price=fill.execution.price,
                        timestamp=datetime.fromisoformat(fill.time),
                    )
                )

            return fills
        except Exception as e:
            logger.error(f"Error getting fills: {e}")
            return []

    def _convert_order_status(self, ib_status: str) -> OrderStatus:
        """Convert IB order status to our OrderStatus enum."""
        status_map = {
            "PendingSubmit": OrderStatus.SUBMITTED,
            "PendingCancel": OrderStatus.SUBMITTED,
            "PreSubmitted": OrderStatus.SUBMITTED,
            "Submitted": OrderStatus.SUBMITTED,
            "ApiPending": OrderStatus.SUBMITTED,
            "Filled": OrderStatus.FILLED,
            "Cancelled": OrderStatus.CANCELLED,
            "Inactive": OrderStatus.CANCELLED,
            "ApiCancelled": OrderStatus.CANCELLED,
        }
        return status_map.get(ib_status, OrderStatus.SUBMITTED)

    def _convert_trade_to_order(self, trade) -> Order:
        """Convert IB trade to our Order type."""
        action = trade.order.action
        side = OrderSide.BUY if action == "BUY" else OrderSide.SELL

        # Determine order type
        if isinstance(trade.order, MarketOrder):
            order_type = OrderType.MARKET
        elif isinstance(trade.order, LimitOrder):
            order_type = OrderType.LIMIT
        elif isinstance(trade.order, StopOrder):
            order_type = OrderType.STOP
        else:
            order_type = OrderType.MARKET

        # Convert time in force
        tif_map = {
            "DAY": TimeInForce.DAY,
            "GTC": TimeInForce.GTC,
            "IOC": TimeInForce.IOC,
            "FOK": TimeInForce.FOK,
        }
        time_in_force = tif_map.get(trade.order.tif, TimeInForce.DAY)

        return Order(
            order_id=str(trade.order.orderId),
            symbol=trade.contract.symbol,
            side=side,
            quantity=trade.order.totalQuantity,
            order_type=order_type,
            time_in_force=time_in_force,
            status=self._convert_order_status(trade.orderStatus.status),
            filled_quantity=trade.orderStatus.filled,
            filled_price=trade.orderStatus.avgFillPrice if trade.orderStatus.avgFillPrice > 0 else None,
            limit_price=getattr(trade.order, "lmtPrice", None),
            stop_price=getattr(trade.order, "auxPrice", None),
            submitted_at=datetime.now(),  # IB doesn't provide submission time easily
        )
