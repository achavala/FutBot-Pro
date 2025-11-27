from __future__ import annotations

from core.live.broker_client import AlpacaBrokerClient, BaseBrokerClient, PaperBrokerClient
# Lazy import IBKR to avoid uvloop conflict with uvicorn
# from core.live.broker_client_ibkr import IBKRBrokerClient
from core.live.data_feed import BaseDataFeed, MockDataFeed, PollingDataFeed
from core.live.data_feed_alpaca import AlpacaDataFeed
# Lazy import IBKR to avoid uvloop conflict with uvicorn
# from core.live.data_feed_ibkr import IBKRDataFeed
from core.live.data_feed_crypto import CryptoDataFeed
from core.live.data_feed_cached import CachedDataFeed
from core.live.executor_live import ExecutionResult, LiveTradeExecutor
from core.live.scheduler import LiveTradingConfig, LiveTradingLoop
from core.live.state_store import StateStore

# Lazy import function for IBKR (only import when actually needed)
def get_ibkr_broker_client():
    """Lazy import IBKR broker client to avoid uvloop conflict."""
    from core.live.broker_client_ibkr import IBKRBrokerClient
    return IBKRBrokerClient

def get_ibkr_data_feed():
    """Lazy import IBKR data feed to avoid uvloop conflict."""
    from core.live.data_feed_ibkr import IBKRDataFeed
    return IBKRDataFeed
from core.live.types import (
    Account,
    Bar,
    Fill,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    TimeInForce,
)

__all__ = [
    "BaseBrokerClient",
    # "IBKRBrokerClient",  # Use get_ibkr_broker_client() instead
    "AlpacaBrokerClient",
    "PaperBrokerClient",
    "BaseDataFeed",
    "PollingDataFeed",
    "MockDataFeed",
    "AlpacaDataFeed",
    # "IBKRDataFeed",  # Use get_ibkr_data_feed() instead
    "CryptoDataFeed",
    "CachedDataFeed",
    "LiveTradeExecutor",
    "ExecutionResult",
    "LiveTradingLoop",
    "LiveTradingConfig",
    "StateStore",
    "Bar",
    "Order",
    "OrderSide",
    "OrderType",
    "OrderStatus",
    "TimeInForce",
    "Position",
    "Account",
    "Fill",
    "get_ibkr_broker_client",
    "get_ibkr_data_feed",
]

