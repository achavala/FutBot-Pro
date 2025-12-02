#!/usr/bin/env python3
"""Simple test for multi-leg data structures and calculations."""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import only what we need (avoid heavy dependencies)
from core.portfolio.options_manager import (
    OptionsPortfolioManager,
    LegFill,
    MultiLegPosition,
)


def test_leg_fill():
    """Test LegFill calculation."""
    print("=" * 60)
    print("TEST 1: LegFill Calculation")
    print("=" * 60)
    
    fill = LegFill(
        leg_type="call",
        option_symbol="SPY251126C00673000",
        strike=673.0,
        quantity=5,
        fill_price=2.50,
        fill_time=datetime.now(),
        status="filled",
    )
    
    expected_cost = 5 * 2.50 * 100  # quantity * price * contract multiplier
    actual_cost = fill.total_cost
    
    print(f"Call Fill: {fill.quantity}x @ ${fill.fill_price:.2f}")
    print(f"Expected Total Cost: ${expected_cost:.2f}")
    print(f"Actual Total Cost: ${actual_cost:.2f}")
    print(f"✅ Match: {'YES' if abs(expected_cost - actual_cost) < 0.01 else 'NO'}")
    
    return abs(expected_cost - actual_cost) < 0.01


def test_multi_leg_pnl():
    """Test multi-leg P&L calculation."""
    print("\n" + "=" * 60)
    print("TEST 2: Multi-Leg P&L Calculation")
    print("=" * 60)
    
    expiration = datetime.now() + timedelta(days=1)
    
    # Create straddle position (short)
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
        both_legs_filled=True,
        total_credit=2400.0,  # (2.50 + 2.30) * 5 * 100
        total_debit=0.0,
    )
    
    print(f"Initial Position:")
    print(f"   Call Entry: ${ml_pos.call_entry_price:.2f}")
    print(f"   Put Entry: ${ml_pos.put_entry_price:.2f}")
    print(f"   Net Premium: ${ml_pos.net_premium:.2f}")
    
    # Update prices (call goes up, put goes down)
    ml_pos.update_prices(
        underlying_price=675.0,
        call_price=3.00,  # Increased (bad for short)
        put_price=1.50,   # Decreased (good for short)
        call_delta=0.55,
        put_delta=-0.45,
        call_theta=-0.05,
        put_theta=-0.05,
        call_iv=0.22,
        put_iv=0.22,
    )
    
    # Calculate expected P&L manually
    # For short: P&L = (entry_price - current_price) * quantity * 100
    call_pnl = (2.50 - 3.00) * 5 * 100  # Lost $250
    put_pnl = (2.30 - 1.50) * 5 * 100   # Made $400
    expected_pnl = call_pnl + put_pnl   # Net: +$150
    
    print(f"\nAfter Price Update:")
    print(f"   Call Price: ${ml_pos.call_current_price:.2f} (was ${ml_pos.call_entry_price:.2f})")
    print(f"   Put Price: ${ml_pos.put_current_price:.2f} (was ${ml_pos.put_entry_price:.2f})")
    print(f"   Expected P&L: ${expected_pnl:.2f}")
    print(f"   Actual P&L: ${ml_pos.combined_unrealized_pnl:.2f}")
    print(f"   ✅ Match: {'YES' if abs(ml_pos.combined_unrealized_pnl - expected_pnl) < 0.01 else 'NO'}")
    
    return abs(ml_pos.combined_unrealized_pnl - expected_pnl) < 0.01


def test_portfolio_manager():
    """Test portfolio manager operations."""
    print("\n" + "=" * 60)
    print("TEST 3: Portfolio Manager Operations")
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
    
    # Add position
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
    
    print(f"✅ Added Position:")
    print(f"   ID: {ml_pos.multi_leg_id}")
    print(f"   Net Premium: ${ml_pos.net_premium:.2f}")
    print(f"   Expected Credit: ${(3.00 + 2.80) * 3 * 100:.2f}")
    print(f"   Actual Credit: ${ml_pos.total_credit:.2f}")
    
    # Verify credit calculation
    expected_credit = (3.00 + 2.80) * 3 * 100
    credit_match = abs(ml_pos.total_credit - expected_credit) < 0.01
    print(f"   ✅ Credit Match: {'YES' if credit_match else 'NO'}")
    
    # Test closing
    trade = portfolio.close_multi_leg_position(
        multi_leg_id=ml_pos.multi_leg_id,
        call_exit_price=2.50,
        put_exit_price=2.20,
        exit_time=datetime.now(),
        underlying_price=600.0,
        reason="Take profit",
        agent="theta_harvester",
    )
    
    print(f"\n✅ Closed Position:")
    print(f"   Combined P&L: ${trade.combined_pnl:.2f}")
    print(f"   Combined P&L %: {trade.combined_pnl_pct:.1f}%")
    
    # Verify P&L calculation
    # Short straddle: profit if both options decrease
    # Call: sold at 3.00, bought back at 2.50 = +$0.50 per contract
    # Put: sold at 2.80, bought back at 2.20 = +$0.60 per contract
    expected_pnl = (3.00 - 2.50) * 3 * 100 + (2.80 - 2.20) * 3 * 100  # 150 + 180 = 330
    pnl_match = abs(trade.combined_pnl - expected_pnl) < 0.01
    
    print(f"   Expected P&L: ${expected_pnl:.2f}")
    print(f"   Actual P&L: ${trade.combined_pnl:.2f}")
    print(f"   ✅ P&L Match: {'YES' if pnl_match else 'NO'}")
    
    # Verify position removed
    pos_removed = portfolio.get_multi_leg_position(ml_pos.multi_leg_id) is None
    print(f"   ✅ Position Removed: {'YES' if pos_removed else 'NO'}")
    
    # Verify trade recorded
    trade_recorded = len(portfolio.multi_leg_trades) > 0
    print(f"   ✅ Trade Recorded: {'YES' if trade_recorded else 'NO'}")
    
    return credit_match and pnl_match and pos_removed and trade_recorded


def test_fill_tracking():
    """Test fill tracking for both legs."""
    print("\n" + "=" * 60)
    print("TEST 4: Fill Tracking")
    print("=" * 60)
    
    portfolio = OptionsPortfolioManager()
    
    expiration = datetime.now() + timedelta(days=1)
    
    # Create position without fills first
    ml_pos = portfolio.add_multi_leg_position(
        symbol="SPY",
        trade_type="strangle",
        direction="long",
        multi_leg_id="SPY_STRANGLE_long_680_660_20251126",
        call_option_symbol="SPY251126C00680000",
        call_strike=680.0,
        call_quantity=2,
        call_entry_price=2.00,
        call_delta=0.30,
        call_theta=-0.03,
        call_iv=0.18,
        put_option_symbol="SPY251126P00660000",
        put_strike=660.0,
        put_quantity=2,
        put_entry_price=1.80,
        put_delta=-0.30,
        put_theta=-0.03,
        put_iv=0.18,
        expiration=expiration,
        entry_time=datetime.now(),
        underlying_price=670.0,
    )
    
    print(f"✅ Created Position (no fills yet):")
    print(f"   Both Legs Filled: {ml_pos.both_legs_filled}")
    print(f"   Expected: False")
    print(f"   ✅ Match: {'YES' if not ml_pos.both_legs_filled else 'NO'}")
    
    # Add call fill
    call_fill = LegFill(
        leg_type="call",
        option_symbol="SPY251126C00680000",
        strike=680.0,
        quantity=2,
        fill_price=2.00,
        fill_time=datetime.now(),
        order_id="order_call_123",
        status="filled",
    )
    
    portfolio.update_multi_leg_fill(ml_pos.multi_leg_id, "call", call_fill)
    ml_pos = portfolio.get_multi_leg_position(ml_pos.multi_leg_id)
    
    print(f"\n✅ Added Call Fill:")
    print(f"   Call Fill Status: {ml_pos.call_fill.status if ml_pos.call_fill else 'None'}")
    print(f"   Both Legs Filled: {ml_pos.both_legs_filled}")
    print(f"   Expected: False (put not filled yet)")
    print(f"   ✅ Match: {'YES' if not ml_pos.both_legs_filled else 'NO'}")
    
    # Add put fill
    put_fill = LegFill(
        leg_type="put",
        option_symbol="SPY251126P00660000",
        strike=660.0,
        quantity=2,
        fill_price=1.80,
        fill_time=datetime.now(),
        order_id="order_put_124",
        status="filled",
    )
    
    portfolio.update_multi_leg_fill(ml_pos.multi_leg_id, "put", put_fill)
    ml_pos = portfolio.get_multi_leg_position(ml_pos.multi_leg_id)
    
    print(f"\n✅ Added Put Fill:")
    print(f"   Put Fill Status: {ml_pos.put_fill.status if ml_pos.put_fill else 'None'}")
    print(f"   Both Legs Filled: {ml_pos.both_legs_filled}")
    print(f"   Expected: True")
    print(f"   ✅ Match: {'YES' if ml_pos.both_legs_filled else 'NO'}")
    
    return ml_pos.both_legs_filled


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("MULTI-LEG EXECUTION - SIMPLE TEST SUITE")
    print("=" * 60)
    print()
    
    tests = [
        ("LegFill Calculation", test_leg_fill),
        ("Multi-Leg P&L Calculation", test_multi_leg_pnl),
        ("Portfolio Manager", test_portfolio_manager),
        ("Fill Tracking", test_fill_tracking),
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


