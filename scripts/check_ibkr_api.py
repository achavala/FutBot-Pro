#!/usr/bin/env python3
"""Check if IB Gateway API is properly enabled and accessible."""

import socket
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def check_port(host, port, timeout=2):
    """Check if a port is open and accepting connections."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        print(f"Error checking port: {e}")
        return False

def test_ibkr_connection(host, port, client_id=999):
    """Test IBKR API connection."""
    try:
        from ib_insync import IB
        
        print(f"🔌 Testing connection to {host}:{port}...")
        ib = IB()
        
        try:
            ib.connect(host, port, clientId=client_id, timeout=5)
            if ib.isConnected():
                print("✅ SUCCESS! IB Gateway API is working!")
                print(f"   Connected: {ib.isConnected()}")
                print(f"   Client ID: {client_id}")
                
                # Try to get account info (tests if API is read-only)
                try:
                    accounts = ib.managedAccounts()
                    if accounts:
                        print(f"   Accounts: {accounts}")
                    print("   ✅ API is NOT read-only (can access account data)")
                except Exception as e:
                    print(f"   ⚠️  Warning: {e}")
                
                ib.disconnect()
                return True
            else:
                print("❌ Connected but isConnected() returns False")
                return False
        except Exception as e:
            error_type = type(e).__name__
            if "ConnectionRefusedError" in error_type or "61" in str(e):
                print(f"❌ Connection refused - Port {port} is not accepting connections")
                print("   → IB Gateway might not be running")
                print("   → Or API socket server is not enabled")
            elif "TimeoutError" in error_type or "timeout" in str(e).lower():
                print(f"❌ Connection timeout - Port {port} is open but API handshake failed")
                print("   → IB Gateway is running but API socket server is NOT enabled")
                print("   → OR API Precautions are blocking the connection")
                print("   → Go to: Configure → API → Settings → Enable Socket Clients")
                print("   → ALSO check: Configure → API → Precautions → Enable all checkboxes")
            elif "Connection reset" in str(e) or "54" in str(e) or "reset by peer" in str(e).lower():
                print(f"❌ Connection reset by peer - Port {port} accepts connection but resets it")
                print("   → This usually means API Precautions are blocking the connection")
                print("   → Go to: Configure → API → Precautions")
                print("   → Enable ALL checkboxes, especially:")
                print("      ✅ Bypass order precautions for API orders")
                print("   → Then RESTART IB Gateway")
            else:
                print(f"❌ Connection failed: {error_type}: {e}")
            return False
    except ImportError:
        print("❌ ib_insync not installed")
        print("   Install with: pip install ib-insync")
        return False

def main():
    print("=" * 60)
    print("IB Gateway API Connection Test")
    print("=" * 60)
    print()
    
    # Check common ports (IB Gateway ports first)
    ports_to_check = [
        (4002, "IB Gateway Paper Trading"),
        (4001, "IB Gateway Live Trading"),
        (7497, "TWS Paper Trading"),
        (7496, "TWS Live Trading"),
    ]
    
    print("📡 Checking ports...")
    open_ports = []
    for port, desc in ports_to_check:
        is_open = check_port("127.0.0.1", port)
        status = "✅ OPEN" if is_open else "❌ CLOSED"
        print(f"   Port {port} ({desc}): {status}")
        if is_open:
            open_ports.append((port, desc))
    
    print()
    
    if not open_ports:
        print("❌ No IB Gateway ports are open!")
        print()
        print("Next steps:")
        print("1. Start IB Gateway (or TWS)")
        print("2. Log in to your account")
        print("3. Enable API: Configure → API → Settings → Enable Socket Clients")
        print("4. Restart IB Gateway")
        return 1
    
    # Test connection to first open port (prefer IB Gateway ports)
    # Sort to prefer IB Gateway ports (4002, 4001) over TWS ports (7497, 7496)
    def port_priority(item):
        port, _ = item
        if port in [4002, 4001]:
            return 0  # IB Gateway ports first
        return 1  # TWS ports second
    
    open_ports_sorted = sorted(open_ports, key=port_priority)
    port, desc = open_ports_sorted[0]
    print(f"🧪 Testing API connection on port {port} ({desc})...")
    print()
    
    success = test_ibkr_connection("127.0.0.1", port)
    
    print()
    if success:
        print("=" * 60)
        print("✅ IB Gateway API is ready!")
        print("=" * 60)
        return 0
    else:
        print("=" * 60)
        print("❌ IB Gateway API is NOT ready")
        print("=" * 60)
        print()
        print("To fix:")
        print("1. Open IB Gateway")
        print("2. Go to: Configure → API → Settings")
        print("3. Check: 'Enable ActiveX and Socket Clients' ✅")
        print("4. Make sure it's NOT read-only")
        print("5. Click OK and RESTART IB Gateway")
        print("6. Wait for IB Gateway to fully connect")
        print("7. Run this script again")
        return 1

if __name__ == "__main__":
    sys.exit(main())

