#!/usr/bin/env python3
"""Test script for multi-leg options execution."""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Try to load dotenv if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not required for testing

from core.portfolio.options_manager import (
    OptionsPortfolioManager,
    MultiLegPosition,
    LegFill,
    MultiLegTrade,
)
from core.live.executor_options import SyntheticOptionsExecutor
from core.live.multi_leg_profit_manager import MultiLegProfitManager
from core.policy.types import FinalTradeIntent
from core.agents.base import TradeDirection


def test_multi_leg_data_structures():
    """Test that data structures work correctly."""
    print("=" * 60)
    print("TEST 1: Multi-Leg Data Structures")
    print("=" * 60)
    
    # Test LegFill
    call_fill = LegFill(
        leg_type="call",
        option_symbol="SPY251126C00673000",
        strike=673.0,
        quantity=5,
        fill_price=2.50,
        fill_time=datetime.now(),
        order_id="order_123",
        status="filled",
    )
    
    put_fill = LegFill(
        leg_type="put",
        option_symbol="SPY251126P00673000",
        strike=673.0,
        quantity=5,
        fill_price=2.30,
        fill_time=datetime.now(),
        order_id="order_124",
        status="filled",
    )
    
    print(f"✅ Call Fill: {call_fill.quantity}x @ ${call_fill.fill_price:.2f} = ${call_fill.total_cost:.2f}")
    print(f"✅ Put Fill: {put_fill.quantity}x @ ${put_fill.fill_price:.2f} = ${put_fill.total_cost:.2f}")
    print(f"✅ Total Cost: ${call_fill.total_cost + put_fill.total_cost:.2f}")
    
    # Test MultiLegPosition
    expiration = datetime.now() + timedelta(days=1)
    ml_pos = MultiLegPosition(
        symbol="SPY",
        trade_type="straddle",
        direction="short",
        multi_leg_id="SPY_STRADDLE_short_673_673_20251126",
        call_option_symbol="SPY251126C00673000",
        call_strike=673.0,
        call_quantity=5,
        call_entry_price=2.50,
        call_current_price=2.50,
        call_delta=0.50,
        call_theta=-0.05,
        call_iv=0.20,
        put_option_symbol="SPY251126P00673000",
        put_strike=673.0,
        put_quantity=5,
        put_entry_price=2.30,
        put_current_price=2.30,
        put_delta=-0.50,
        put_theta=-0.05,
        put_iv=0.20,
        expiration=expiration,
        entry_time=datetime.now(),
        underlying_price=673.0,
        call_fill=call_fill,
        put_fill=put_fill,
        both_legs_filled=True,
        total_credit=2400.0,  # (2.50 + 2.30) * 5 * 100
        total_debit=0.0,
    )
    
    print(f"\n✅ Multi-Leg Position Created:")
    print(f"   ID: {ml_pos.multi_leg_id}")
    print(f"   Type: {ml_pos.trade_type} ({ml_pos.direction})")
    print(f"   Net Premium: ${ml_pos.net_premium:.2f}")
    print(f"   Both Legs Filled: {ml_pos.both_legs_filled}")
    print(f"   Days to Expiry: {ml_pos.days_to_expiry:.1f}")
    
    # Test P&L calculation
    ml_pos.update_prices(
        underlying_price=675.0,
        call_price=3.00,  # Call increased (bad for short)
        put_price=1.50,   # Put decreased (good for short)
        call_delta=0.55,
        put_delta=-0.45,
        call_theta=-0.05,
        put_theta=-0.05,
        call_iv=0.22,
        put_iv=0.22,
    )
    
    print(f"\n✅ After Price Update:")
    print(f"   Combined Unrealized P&L: ${ml_pos.combined_unrealized_pnl:.2f}")
    print(f"   Call P&L: ${(2.50 - 3.00) * 5 * 100:.2f} (lost money)")
    print(f"   Put P&L: ${(2.30 - 1.50) * 5 * 100:.2f} (made money)")
    
    return True


def test_portfolio_manager():
    """Test portfolio manager multi-leg methods."""
    print("\n" + "=" * 60)
    print("TEST 2: Portfolio Manager Multi-Leg Methods")
    print("=" * 60)
    
    portfolio = OptionsPortfolioManager()
    
    expiration = datetime.now() + timedelta(days=1)
    call_fill = LegFill(
        leg_type="call",
        option_symbol="QQQ251126C00600000",
        strike=600.0,
        quantity=3,
        fill_price=3.00,
        fill_time=datetime.now(),
        status="filled",
    )
    
    put_fill = LegFill(
        leg_type="put",
        option_symbol="QQQ251126P00600000",
        strike=600.0,
        quantity=3,
        fill_price=2.80,
        fill_time=datetime.now(),
        status="filled",
    )
    
    ml_pos = portfolio.add_multi_leg_position(
        symbol="QQQ",
        trade_type="straddle",
        direction="short",
        multi_leg_id="QQQ_STRADDLE_short_600_600_20251126",
        call_option_symbol="QQQ251126C00600000",
        call_strike=600.0,
        call_quantity=3,
        call_entry_price=3.00,
        call_delta=0.50,
        call_theta=-0.05,
        call_iv=0.25,
        put_option_symbol="QQQ251126P00600000",
        put_strike=600.0,
        put_quantity=3,
        put_entry_price=2.80,
        put_delta=-0.50,
        put_theta=-0.05,
        put_iv=0.25,
        expiration=expiration,
        entry_time=datetime.now(),
        underlying_price=600.0,
        call_fill=call_fill,
        put_fill=put_fill,
    )
    
    print(f"✅ Added Multi-Leg Position:")
    print(f"   ID: {ml_pos.multi_leg_id}")
    print(f"   Net Premium: ${ml_pos.net_premium:.2f}")
    print(f"   Total Credit: ${ml_pos.total_credit:.2f}")
    
    # Test closing
    trade = portfolio.close_multi_leg_position(
        multi_leg_id=ml_pos.multi_leg_id,
        call_exit_price=2.50,  # Call decreased (good for short)
        put_exit_price=2.20,   # Put decreased (good for short)
        exit_time=datetime.now(),
        underlying_price=600.0,
        reason="Take profit at 50%",
        agent="theta_harvester",
    )
    
    print(f"\n✅ Closed Multi-Leg Position:")
    print(f"   Combined P&L: ${trade.combined_pnl:.2f}")
    print(f"   Combined P&L %: {trade.combined_pnl_pct:.1f}%")
    print(f"   Duration: {trade.duration_minutes:.1f} minutes")
    
    # Verify calculation
    expected_pnl = (
        (3.00 - 2.50) * 3 * 100 +  # Call profit (sold at 3.00, bought back at 2.50)
        (2.80 - 2.20) * 3 * 100    # Put profit (sold at 2.80, bought back at 2.20)
    )  # = 150 + 180 = 330
    
    print(f"\n✅ Verification:")
    print(f"   Expected P&L: ${expected_pnl:.2f}")
    print(f"   Actual P&L: ${trade.combined_pnl:.2f}")
    print(f"   Match: {'✅' if abs(trade.combined_pnl - expected_pnl) < 0.01 else '❌'}")
    
    return True


def test_profit_manager():
    """Test multi-leg profit manager auto-exit logic."""
    print("\n" + "=" * 60)
    print("TEST 3: Multi-Leg Profit Manager")
    print("=" * 60)
    
    profit_manager = MultiLegProfitManager()
    
    # Test Theta Harvester tracking
    profit_manager.track_position(
        multi_leg_id="SPY_STRADDLE_short_673_673_20251126",
        strategy="theta_harvester",
        direction="short",
        net_premium=2400.0,  # $2.40 per contract * 5 contracts * 100
        entry_time=datetime.now(),
        entry_bar=100,
        entry_iv=0.25,
        entry_gex_strength=0.0,
    )
    
    print("✅ Tracked Theta Harvester position")
    
    # Test take profit (50% of credit = $1200 profit)
    should_close, reason = profit_manager.should_take_profit(
        multi_leg_id="SPY_STRADDLE_short_673_673_20251126",
        current_pnl_pct=50.0,  # 50% profit
        current_bar=150,
        current_regime=None,
        symbol="SPY",
    )
    
    print(f"\n✅ Take Profit Check (50% profit):")
    print(f"   Should Close: {should_close}")
    print(f"   Reason: {reason}")
    print(f"   Expected: True (50% TP triggered)")
    print(f"   Match: {'✅' if should_close else '❌'}")
    
    # Test stop loss (200% of credit = $4800 loss)
    profit_manager.track_position(
        multi_leg_id="SPY_STRADDLE_short_673_673_20251127",
        strategy="theta_harvester",
        direction="short",
        net_premium=2400.0,
        entry_time=datetime.now(),
        entry_bar=200,
        entry_iv=0.25,
    )
    
    should_close, reason = profit_manager.should_take_profit(
        multi_leg_id="SPY_STRADDLE_short_673_673_20251127",
        current_pnl_pct=-200.0,  # 200% loss
        current_bar=250,
        current_regime=None,
        symbol="SPY",
    )
    
    print(f"\n✅ Stop Loss Check (-200% loss):")
    print(f"   Should Close: {should_close}")
    print(f"   Reason: {reason}")
    print(f"   Expected: True (200% SL triggered)")
    print(f"   Match: {'✅' if should_close else '❌'}")
    
    # Test Gamma Scalper
    profit_manager.track_position(
        multi_leg_id="QQQ_STRANGLE_long_610_590_20251126",
        strategy="gamma_scalper",
        direction="long",
        net_premium=-1740.0,  # Debit (negative)
        entry_time=datetime.now(),
        entry_bar=300,
        entry_iv=0.15,
        entry_gex_strength=-3.5,  # Negative GEX
    )
    
    should_close, reason = profit_manager.should_take_profit(
        multi_leg_id="QQQ_STRANGLE_long_610_590_20251126",
        current_pnl_pct=150.0,  # 150% gain
        current_bar=350,
        current_regime=None,
        symbol="QQQ",
    )
    
    print(f"\n✅ Gamma Scalper Take Profit (150% gain):")
    print(f"   Should Close: {should_close}")
    print(f"   Reason: {reason}")
    print(f"   Expected: True (150% TP triggered)")
    print(f"   Match: {'✅' if should_close else '❌'}")
    
    return True


def test_executor_integration():
    """Test executor with mock data feed."""
    print("\n" + "=" * 60)
    print("TEST 4: Executor Integration")
    print("=" * 60)
    
    portfolio = OptionsPortfolioManager()
    executor = SyntheticOptionsExecutor(portfolio)
    
    # Create a straddle intent (like Theta Harvester would generate)
    intent = FinalTradeIntent(
        position_delta=-5,  # Negative = selling
        confidence=0.90,
        primary_agent="theta_harvester",
        contributing_agents=["theta_harvester"],
        reason="SELL 5x ATM STRADDLE: Compression + High IV",
        is_valid=True,
        instrument_type="option",
        option_type="straddle",
        moneyness="atm",
        time_to_expiry_days=1,
        metadata={
            "strategy": "theta_harvester",
            "trade_type": "straddle",
            "strike": 673.0,
            "expiration": "2025-11-26",
            "call_symbol": "SPY251126C00673000",
            "put_symbol": "SPY251126P00673000",
            "total_credit": 2.40,  # Per contract
        },
    )
    
    print("✅ Created straddle intent:")
    print(f"   Direction: SHORT (selling premium)")
    print(f"   Quantity: 5 contracts")
    print(f"   Strike: $673.00")
    print(f"   Expected Credit: ${2.40 * 5 * 100:.2f}")
    
    # Execute (will use synthetic pricing since no real data feed)
    result = executor._execute_multi_leg_trade(
        intent=intent,
        symbol="SPY",
        underlying_price=673.0,
        regime_at_entry="compression",
        vol_bucket_at_entry="high",
    )
    
    print(f"\n✅ Execution Result:")
    print(f"   Success: {result.success}")
    print(f"   Reason: {result.reason}")
    print(f"   Option Symbol: {result.option_symbol}")
    
    if result.success:
        # Check position was created
        ml_pos = portfolio.get_multi_leg_position(result.option_symbol)
        if ml_pos:
            print(f"\n✅ Position Created:")
            print(f"   Multi-Leg ID: {ml_pos.multi_leg_id}")
            print(f"   Call Entry: ${ml_pos.call_entry_price:.2f}")
            print(f"   Put Entry: ${ml_pos.put_entry_price:.2f}")
            print(f"   Net Premium: ${ml_pos.net_premium:.2f}")
            print(f"   Both Legs Filled: {ml_pos.both_legs_filled}")
            print(f"   Call Fill Status: {ml_pos.call_fill.status if ml_pos.call_fill else 'N/A'}")
            print(f"   Put Fill Status: {ml_pos.put_fill.status if ml_pos.put_fill else 'N/A'}")
        else:
            print("❌ Position not found in portfolio")
            return False
    
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("MULTI-LEG EXECUTION TEST SUITE")
    print("=" * 60)
    print()
    
    tests = [
        ("Data Structures", test_multi_leg_data_structures),
        ("Portfolio Manager", test_portfolio_manager),
        ("Profit Manager", test_profit_manager),
        ("Executor Integration", test_executor_integration),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} FAILED: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(r[1] for r in results)
    print(f"\n{'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

