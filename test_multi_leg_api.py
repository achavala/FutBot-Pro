#!/usr/bin/env python3
"""Test multi-leg API endpoints."""

import requests
import json
import time
from datetime import datetime

API_BASE = "http://localhost:8000"


def test_api_endpoints():
    """Test API endpoints for multi-leg positions and trades."""
    print("=" * 60)
    print("MULTI-LEG API ENDPOINT TESTS")
    print("=" * 60)
    print()
    
    # Test 1: Get options positions (should include multi_leg_positions)
    print("TEST 1: GET /options/positions")
    print("-" * 60)
    try:
        response = requests.get(f"{API_BASE}/options/positions", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: {response.status_code}")
            print(f"   Single-leg positions: {len(data.get('positions', []))}")
            print(f"   Multi-leg positions: {len(data.get('multi_leg_positions', []))}")
            
            # Show multi-leg positions if any
            if data.get('multi_leg_positions'):
                print(f"\n   Multi-Leg Positions:")
                for pos in data['multi_leg_positions']:
                    print(f"      - {pos['trade_type'].upper()} {pos['direction']} {pos['symbol']}")
                    print(f"        Call: ${pos['call_strike']:.2f} @ ${pos['call_entry_price']:.2f}")
                    print(f"        Put: ${pos['put_strike']:.2f} @ ${pos['put_entry_price']:.2f}")
                    print(f"        P&L: ${pos['combined_unrealized_pnl']:.2f}")
                    print(f"        Filled: {pos['both_legs_filled']}")
        else:
            print(f"⚠️ Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Is it running on port 8000?")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    print()
    
    # Test 2: Get multi-leg trades
    print("TEST 2: GET /trades/options/multi-leg")
    print("-" * 60)
    try:
        response = requests.get(f"{API_BASE}/trades/options/multi-leg?limit=10", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: {response.status_code}")
            print(f"   Multi-leg trades: {len(data.get('trades', []))}")
            
            # Show trades if any
            if data.get('trades'):
                print(f"\n   Recent Trades:")
                for trade in data['trades'][:3]:  # Show first 3
                    pnl_color = "✅" if trade['combined_pnl'] >= 0 else "❌"
                    print(f"      {pnl_color} {trade['trade_type'].upper()} {trade['direction']}")
                    print(f"         P&L: ${trade['combined_pnl']:.2f} ({trade['combined_pnl_pct']:.1f}%)")
                    print(f"         Duration: {trade['duration_minutes']:.1f}m")
        else:
            print(f"⚠️ Status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    print()
    
    # Test 3: Check live status
    print("TEST 3: GET /live/status")
    print("-" * 60)
    try:
        response = requests.get(f"{API_BASE}/live/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: {response.status_code}")
            print(f"   Running: {data.get('is_running', False)}")
            print(f"   Mode: {data.get('mode', 'unknown')}")
            print(f"   Bar Count: {data.get('bar_count', 0)}")
            print(f"   Symbols: {data.get('symbols', [])}")
        else:
            print(f"⚠️ Status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    print()
    print("=" * 60)
    print("✅ API TESTS COMPLETE")
    print("=" * 60)
    print()
    print("Next Steps:")
    print("1. Start live trading to generate multi-leg positions")
    print("2. Check dashboard at http://localhost:8000/dashboard")
    print("3. Navigate to Analytics → Options Dashboard")
    print("4. View Multi-Leg Positions and Trade History tables")
    
    return True


if __name__ == "__main__":
    test_api_endpoints()


