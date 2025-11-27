#!/usr/bin/env python3
"""Diagnose IBKR connection issues."""

import socket
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def check_port(host, port):
    """Check if port is open."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

def main():
    print("🔍 IBKR Connection Diagnostics")
    print("=" * 50)
    print()
    
    # Check ports
    ports = [4002, 7497, 7496, 4001]
    open_ports = []
    
    print("Port Status:")
    for port in ports:
        is_open = check_port("127.0.0.1", port)
        status = "✅ OPEN" if is_open else "❌ CLOSED"
        print(f"  Port {port}: {status}")
        if is_open:
            open_ports.append(port)
    
    print()
    
    if not open_ports:
        print("❌ No ports are open")
        print()
        print("Please check:")
        print("1. IB Gateway is running and logged in")
        print("2. API is enabled: Configure → API → Settings")
        print("3. 'Enable ActiveX and Socket Clients' is checked")
        return 1
    
    print(f"✅ Found {len(open_ports)} open port(s): {open_ports}")
    print()
    
    # Try to connect with ib_insync
    print("Testing ib_insync connection...")
    try:
        from ib_insync import IB
        
        for port in open_ports:
            print(f"\nTrying port {port}...")
            try:
                ib = IB()
                ib.connect('127.0.0.1', port, clientId=999, timeout=5)
                print(f"✅ Successfully connected on port {port}!")
                
                # Get account info
                accounts = ib.managedAccounts()
                if accounts:
                    print(f"   Found account(s): {accounts}")
                else:
                    print("   No accounts found")
                
                ib.disconnect()
                print(f"\n✅ Port {port} is working correctly!")
                print(f"\n💡 Use port {port} in your connection settings")
                return 0
            except Exception as e:
                print(f"   ❌ Connection failed: {e}")
                continue
        
        print("\n❌ Could not connect to any open port")
        print("\nPossible issues:")
        print("1. API might be in read-only mode")
        print("2. Client ID might be in use")
        print("3. IB Gateway might need restart after API changes")
        print("4. Check IB Gateway logs for errors")
        return 1
        
    except ImportError:
        print("❌ ib_insync not installed")
        print("Run: pip install ib-insync")
        return 1

if __name__ == "__main__":
    sys.exit(main())

