#!/usr/bin/env python3
"""Validation script for historical replay engine."""

import requests
import json
import time
import sys
from datetime import datetime, timedelta

API_BASE = "http://localhost:8000"

def test_basic_historical_run():
    """Test 1: Basic historical run from a known date."""
    print("=" * 60)
    print("TEST 1: Basic Historical Run")
    print("=" * 60)
    
    # Stop any existing simulation first
    try:
        requests.post(f"{API_BASE}/live/stop", timeout=5)
        time.sleep(2)
    except:
        pass
    
    # Use date 10 days ago
    start_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
    
    payload = {
        "symbols": ["SPY"],
        "broker_type": "cached",
        "offline_mode": True,
        "start_date": start_date,
        "fixed_investment_amount": 10000.0,
        "replay_speed": 600.0
    }
    
    print(f"📤 Starting simulation from {start_date}...")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(f"{API_BASE}/live/start", json=payload, timeout=10)
        print(f"\n📥 Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("\n✅ Simulation started successfully!")
            print("🔍 Waiting 5 seconds, then checking status...")
            time.sleep(5)
            
            status = requests.get(f"{API_BASE}/live/status").json()
            print(f"\n📊 Status after 5 seconds:")
            print(json.dumps(status, indent=2))
            
            if status.get("is_running") and status.get("bar_count", 0) > 0:
                print("\n✅ TEST 1 PASSED: Simulation is running and processing bars!")
                return True
            else:
                print("\n❌ TEST 1 FAILED: Simulation not processing bars")
                return False
        else:
            print(f"\n❌ TEST 1 FAILED: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ TEST 1 ERROR: {e}")
        return False

def test_multi_symbol():
    """Test 2: Multi-symbol run."""
    print("\n" + "=" * 60)
    print("TEST 2: Multi-Symbol Run")
    print("=" * 60)
    
    start_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
    
    payload = {
        "symbols": ["QQQ", "SPY"],
        "broker_type": "cached",
        "offline_mode": True,
        "start_date": start_date,
        "replay_speed": 600.0
    }
    
    print(f"📤 Starting multi-symbol simulation...")
    
    try:
        # Stop any existing simulation first
        requests.post(f"{API_BASE}/live/stop", timeout=5)
        time.sleep(2)
        
        response = requests.post(f"{API_BASE}/live/start", json=payload, timeout=10)
        
        if response.status_code == 200:
            print("✅ Simulation started")
            time.sleep(5)
            
            status = requests.get(f"{API_BASE}/live/status").json()
            bars_per_symbol = status.get("bars_per_symbol", {})
            
            print(f"\n📊 Bars per symbol: {bars_per_symbol}")
            
            if "QQQ" in bars_per_symbol and "SPY" in bars_per_symbol:
                qqq_bars = bars_per_symbol.get("QQQ", 0)
                spy_bars = bars_per_symbol.get("SPY", 0)
                
                if qqq_bars > 0 and spy_bars > 0:
                    print(f"\n✅ TEST 2 PASSED: Both symbols processing (QQQ: {qqq_bars}, SPY: {spy_bars})")
                    return True
                else:
                    print(f"\n❌ TEST 2 FAILED: One symbol not processing")
                    return False
            else:
                print("\n❌ TEST 2 FAILED: bars_per_symbol not in status")
                return False
        else:
            print(f"\n❌ TEST 2 FAILED: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ TEST 2 ERROR: {e}")
        return False

def test_replay_speed():
    """Test 3: Confirm replay speed is actually fast."""
    print("\n" + "=" * 60)
    print("TEST 3: Replay Speed Validation")
    print("=" * 60)
    
    start_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
    
    payload = {
        "symbols": ["SPY"],
        "broker_type": "cached",
        "offline_mode": True,
        "start_date": start_date,
        "replay_speed": 600.0
    }
    
    try:
        requests.post(f"{API_BASE}/live/stop", timeout=5)
        time.sleep(2)
        
        response = requests.post(f"{API_BASE}/live/start", json=payload, timeout=10)
        
        if response.status_code == 200:
            print("✅ Simulation started")
            
            # Get initial bar count
            initial_status = requests.get(f"{API_BASE}/live/status").json()
            initial_bars = initial_status.get("bar_count", 0)
            
            print(f"📊 Initial bar count: {initial_bars}")
            print("⏱️  Waiting 10 seconds...")
            time.sleep(10)
            
            # Get final bar count
            final_status = requests.get(f"{API_BASE}/live/status").json()
            final_bars = final_status.get("bar_count", 0)
            
            bars_processed = final_bars - initial_bars
            bars_per_second = bars_processed / 10.0
            
            print(f"📊 Final bar count: {final_bars}")
            print(f"📊 Bars processed in 10s: {bars_processed}")
            print(f"📊 Speed: {bars_per_second:.1f} bars/second")
            
            # Should process at least 50 bars in 10 seconds at 600x speed
            if bars_per_second >= 5.0:
                print(f"\n✅ TEST 3 PASSED: Fast replay confirmed ({bars_per_second:.1f} bars/sec)")
                return True
            else:
                print(f"\n❌ TEST 3 FAILED: Too slow ({bars_per_second:.1f} bars/sec, expected >= 5.0)")
                return False
        else:
            print(f"\n❌ TEST 3 FAILED: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ TEST 3 ERROR: {e}")
        return False

def test_stop_cleanly():
    """Test 4: Confirm it stops cleanly."""
    print("\n" + "=" * 60)
    print("TEST 4: Clean Stop")
    print("=" * 60)
    
    try:
        print("📤 Stopping simulation...")
        response = requests.post(f"{API_BASE}/live/stop", timeout=5)
        
        if response.status_code == 200:
            time.sleep(2)
            status = requests.get(f"{API_BASE}/live/status").json()
            
            print(f"📊 Status after stop: {json.dumps(status, indent=2)}")
            
            if not status.get("is_running", True):
                print("\n✅ TEST 4 PASSED: Simulation stopped cleanly")
                return True
            else:
                print("\n❌ TEST 4 FAILED: Still running after stop")
                return False
        else:
            print(f"\n❌ TEST 4 FAILED: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ TEST 4 ERROR: {e}")
        return False

def main():
    """Run all validation tests."""
    print("\n" + "=" * 60)
    print("🚀 HISTORICAL REPLAY ENGINE VALIDATION")
    print("=" * 60)
    print()
    
    results = []
    
    # Run tests
    results.append(("Basic Historical Run", test_basic_historical_run()))
    results.append(("Multi-Symbol Run", test_multi_symbol()))
    results.append(("Replay Speed", test_replay_speed()))
    results.append(("Clean Stop", test_stop_cleanly()))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 VALIDATION SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Replay engine is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check logs for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

