#!/usr/bin/env python3
"""Test script to verify dashboard endpoint works correctly."""

import requests
import sys

def test_dashboard():
    """Test the dashboard endpoint."""
    url = "http://localhost:8000/"
    
    print("Testing FutBot Dashboard endpoint...")
    print(f"URL: {url}")
    print()
    
    try:
        response = requests.get(url, timeout=5)
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type', 'Not set')}")
        print()
        
        content = response.text
        print(f"Response length: {len(content)} bytes")
        print()
        
        if response.headers.get('Content-Type', '').startswith('text/html'):
            if content.strip().startswith('<!DOCTYPE') or content.strip().startswith('<html'):
                print("✅ SUCCESS: Dashboard HTML is being served correctly!")
                print(f"   First 100 chars: {content[:100]}")
                return True
            else:
                print("❌ ERROR: Content-Type is HTML but content doesn't look like HTML")
                print(f"   First 200 chars: {content[:200]}")
                return False
        else:
            print("❌ ERROR: Content-Type is not text/html")
            print(f"   Content-Type: {response.headers.get('Content-Type')}")
            print(f"   First 200 chars: {content[:200]}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Cannot connect to server at http://localhost:8000")
        print("   Make sure the FastAPI server is running:")
        print("   python main.py --mode api --port 8000")
        return False
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    success = test_dashboard()
    sys.exit(0 if success else 1)

