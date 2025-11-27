#!/usr/bin/env python3
"""Check which IBKR port is open."""

import socket
import sys

def check_port(host, port):
    """Check if a port is open."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

def main():
    print("🔍 Checking IBKR API Ports")
    print("=" * 40)
    print()
    
    ports_to_check = [
        (7497, "Paper Trading"),
        (7496, "Live Trading"),
        (4001, "TWS Default"),
        (4002, "TWS Alternative"),
    ]
    
    open_ports = []
    for port, name in ports_to_check:
        if check_port("127.0.0.1", port):
            print(f"✅ Port {port} ({name}) is OPEN")
            open_ports.append((port, name))
        else:
            print(f"❌ Port {port} ({name}) is CLOSED")
    
    print()
    if open_ports:
        print("✅ Found open ports:")
        for port, name in open_ports:
            print(f"   - Port {port} ({name})")
        print()
        print("💡 Make sure API is enabled in IB Gateway:")
        print("   Configure → API → Settings → Enable ActiveX and Socket Clients")
    else:
        print("❌ No open ports found")
        print()
        print("Troubleshooting:")
        print("1. Ensure IB Gateway is running")
        print("2. Go to: Configure → API → Settings")
        print("3. Check 'Enable ActiveX and Socket Clients'")
        print("4. Set Socket port to 7497 (paper) or 7496 (live)")
        print("5. Click OK and restart IB Gateway if needed")
    
    return 0 if open_ports else 1

if __name__ == "__main__":
    sys.exit(main())

