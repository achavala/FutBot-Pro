from __future__ import annotations

from datetime import datetime

import pytest

from core.portfolio.manager import PortfolioManager


def test_portfolio_initialization():
    portfolio = PortfolioManager(initial_capital=100000.0, symbol="QQQ")
    assert portfolio.initial_capital == 100000.0
    assert portfolio.current_capital == 100000.0
    assert portfolio.symbol == "QQQ"
    assert len(portfolio.positions) == 0


def test_add_position():
    portfolio = PortfolioManager(100000.0, "QQQ")
    timestamp = datetime.now()
    portfolio.add_position("QQQ", 100.0, 150.0, timestamp)

    assert "QQQ" in portfolio.positions
    pos = portfolio.positions["QQQ"]
    assert pos.quantity == 100.0
    assert pos.entry_price == 150.0


def test_close_position():
    portfolio = PortfolioManager(100000.0, "QQQ")
    timestamp = datetime.now()
    portfolio.add_position("QQQ", 100.0, 150.0, timestamp)

    exit_time = datetime.now()
    trade = portfolio.close_position("QQQ", 155.0, exit_time, "test", "test_agent")

    assert trade is not None
    assert trade.pnl == 500.0  # (155 - 150) * 100
    assert trade.pnl_pct == pytest.approx(3.33, abs=0.1)
    assert "QQQ" not in portfolio.positions
    assert portfolio.current_capital == 100500.0


def test_apply_position_delta():
    portfolio = PortfolioManager(100000.0, "QQQ")
    timestamp = datetime.now()

    # Buy
    trade1 = portfolio.apply_position_delta(100.0, 150.0, timestamp)
    assert trade1 is None  # No trade closed
    assert portfolio.positions["QQQ"].quantity == 100.0

    # Sell (close position)
    trade2 = portfolio.apply_position_delta(-100.0, 155.0, timestamp)
    assert trade2 is not None
    assert trade2.pnl == 500.0


def test_get_total_value():
    portfolio = PortfolioManager(100000.0, "QQQ")
    timestamp = datetime.now()
    portfolio.add_position("QQQ", 100.0, 150.0, timestamp)

    # Update price
    portfolio.update_position("QQQ", 155.0)
    total_value = portfolio.get_total_value(155.0)

    assert total_value == pytest.approx(100500.0, abs=1.0)


def test_equity_curve():
    portfolio = PortfolioManager(100000.0, "QQQ")
    portfolio.record_equity(150.0)
    portfolio.record_equity(155.0)

    assert len(portfolio.equity_curve) == 2
    assert portfolio.equity_curve[0] == 100000.0


def test_get_total_return_pct():
    portfolio = PortfolioManager(100000.0, "QQQ")
    # Add a position that increases value
    timestamp = datetime.now()
    portfolio.add_position("QQQ", 666.0, 150.0, timestamp)  # ~$100k position
    portfolio.update_position("QQQ", 157.5)  # 5% gain on position
    portfolio.record_equity(157.5)

    # Should be approximately 5% return (gain on position / initial capital)
    return_pct = portfolio.get_total_return_pct()
    assert return_pct > 0
    assert return_pct == pytest.approx(5.0, abs=1.0)


def test_get_max_drawdown():
    portfolio = PortfolioManager(100000.0, "QQQ")
    timestamp = datetime.now()
    portfolio.add_position("QQQ", 100.0, 150.0, timestamp)
    
    # Peak at 110k
    portfolio.update_position("QQQ", 165.0)  # 10% gain
    portfolio.record_equity(165.0)
    
    # Drawdown to 105k
    portfolio.update_position("QQQ", 157.5)  # 5% gain
    portfolio.record_equity(157.5)
    
    # More drawdown to 100k
    portfolio.update_position("QQQ", 150.0)  # back to entry
    portfolio.record_equity(150.0)

    max_dd = portfolio.get_max_drawdown()
    assert max_dd > 0


def test_get_win_rate():
    portfolio = PortfolioManager(100000.0, "QQQ")
    timestamp = datetime.now()

    # Winning trade
    portfolio.add_position("QQQ", 100.0, 150.0, timestamp)
    portfolio.close_position("QQQ", 155.0, timestamp, "win", "agent")

    # Losing trade
    portfolio.add_position("QQQ", 100.0, 150.0, timestamp)
    portfolio.close_position("QQQ", 145.0, timestamp, "loss", "agent")

    win_rate = portfolio.get_win_rate()
    assert win_rate == 50.0

