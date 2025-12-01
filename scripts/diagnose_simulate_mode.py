#!/usr/bin/env python3
"""Diagnostic script for Simulate mode to identify failures in the pipeline."""

import requests
import json
import sys

def test_simulate_mode():
    """Test the simulate mode endpoint with detailed logging."""
    url = "http://localhost:8000/live/start"
    
    payload = {
        "symbols": ["QQQ", "SPY"],
        "broker_type": "cached",
        "offline_mode": True,
        "fixed_investment_amount": 10000.0
    }
    
    print("=" * 60)
    print("🔍 SIMULATE MODE DIAGNOSTIC TEST")
    print("=" * 60)
    print(f"\n📤 Sending request to: {url}")
    print(f"📦 Payload:")
    print(json.dumps(payload, indent=2))
    print("\n" + "-" * 60)
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        
        print(f"\n📥 Response Status: {response.status_code}")
        print(f"📥 Response Headers: {dict(response.headers)}")
        
        try:
            response_data = response.json()
            print(f"📥 Response Body:")
            print(json.dumps(response_data, indent=2))
        except:
            print(f"📥 Response Text: {response.text}")
        
        print("\n" + "-" * 60)
        
        if response.status_code == 200:
            print("✅ Request succeeded!")
            print("\n🔍 Next steps:")
            print("1. Check server logs for:")
            print("   - '🔵 START REQUEST' line")
            print("   - '✅ CachedDataFeed created'")
            print("   - '🔵 Starting live trading'")
            print("   - '✅ bot_manager.start_live_trading() completed'")
            print("   - '[LiveLoop] Starting loop...'")
            print("\n2. Check if live loop is running:")
            print("   curl http://localhost:8000/health")
            return True
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print("\n🔍 Check server logs for error details")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Cannot connect to server at http://localhost:8000")
        print("   Make sure the FastAPI server is running:")
        print("   python main.py --mode api --port 8000")
        return False
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_simulate_mode()
    sys.exit(0 if success else 1)


