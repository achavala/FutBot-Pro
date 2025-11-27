from __future__ import annotations

import pytest

from core.live import MockDataFeed, PaperBrokerClient, LiveTradeExecutor, LiveTradingConfig
from core.live.types import OrderSide, OrderType, TimeInForce
from core.policy.types import FinalTradeIntent


def test_paper_broker_client():
    """Test paper broker client."""
    broker = PaperBrokerClient(initial_cash=100000.0)
    account = broker.get_account()
    assert account.cash == 100000.0
    assert account.equity == 100000.0


def test_paper_broker_order():
    """Test paper broker order submission."""
    broker = PaperBrokerClient(initial_cash=100000.0)
    order = broker.submit_order(
        symbol="QQQ",
        side=OrderSide.BUY,
        quantity=10.0,
        order_type=OrderType.MARKET,
        time_in_force=TimeInForce.DAY,
    )
    assert order.status.value == "filled"
    assert order.filled_quantity == 10.0

    account = broker.get_account()
    assert account.cash < 100000.0  # Cash reduced


def test_mock_data_feed():
    """Test mock data feed."""
    feed = MockDataFeed(initial_price=100.0)
    assert feed.connect()
    assert feed.subscribe(["QQQ"])

    bar = feed.get_next_bar("QQQ")
    assert bar is not None
    assert bar.symbol == "QQQ"
    assert bar.close > 0


def test_live_executor():
    """Test live trade executor."""
    broker = PaperBrokerClient(initial_cash=100000.0)
    executor = LiveTradeExecutor(broker)

    intent = FinalTradeIntent(
        position_delta=0.1,
        confidence=0.8,
        primary_agent="test_agent",
        contributing_agents=["test_agent"],
        reason="test",
        is_valid=True,
    )

    result = executor.apply_intent(intent, "QQQ", 150.0, 0.0)
    assert result.success
    assert result.order is not None


def test_live_executor_invalid_intent():
    """Test executor with invalid intent."""
    broker = PaperBrokerClient(initial_cash=100000.0)
    executor = LiveTradeExecutor(broker)

    intent = FinalTradeIntent(
        position_delta=0.0,
        confidence=0.8,
        primary_agent="test_agent",
        contributing_agents=[],
        reason="test",
        is_valid=False,
    )

    result = executor.apply_intent(intent, "QQQ", 150.0, 0.0)
    assert not result.success


def test_state_store():
    """Test state store save/load."""
    from pathlib import Path
    from core.live import StateStore

    state_file = Path("state/test_state.json")
    store = StateStore(state_file)

    # Save state
    state = {"bar_count": 100, "last_price": 150.0}
    store.save_state(state)

    # Load state
    loaded = store.load_state()
    assert loaded["bar_count"] == 100
    assert loaded["last_price"] == 150.0

    # Cleanup
    store.clear_state()

