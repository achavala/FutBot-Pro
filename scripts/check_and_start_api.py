#!/usr/bin/env python3
"""
Check if FastAPI server is running and start it if needed.
"""

import sys
import os
import time
import subprocess
from pathlib import Path
import urllib.request
import urllib.error

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Colors
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'

API_URL = "http://localhost:8000"
HEALTH_ENDPOINT = f"{API_URL}/health"


def check_server_running():
    """Check if FastAPI server is running."""
    try:
        req = urllib.request.Request(HEALTH_ENDPOINT)
        with urllib.request.urlopen(req, timeout=2) as response:
            if response.status == 200:
                return True, "Server is running"
    except urllib.error.URLError:
        return False, "Server not responding"
    except Exception as e:
        return False, f"Error checking server: {e}"
    
    return False, "Server not running"


def find_api_server_process():
    """Find if API server process is running."""
    try:
        # Check for uvicorn or python processes running fastapi_app
        result = subprocess.run(
            ["pgrep", "-f", "fastapi_app|uvicorn.*fastapi"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            return True, pids
        return False, []
    except Exception:
        return False, []


def start_api_server():
    """Start the FastAPI server."""
    print(f"\n{BLUE}Starting FastAPI server...{NC}")
    
    # Find the fastapi_app.py file
    fastapi_app_path = Path("ui/fastapi_app.py")
    if not fastapi_app_path.exists():
        print(f"{RED}❌ FastAPI app not found at {fastapi_app_path}{NC}")
        return False
    
    # Start server in background
    try:
        # Use uvicorn to start the server
        cmd = [
            sys.executable, "-m", "uvicorn",
            "ui.fastapi_app:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ]
        
        print(f"{BLUE}Running: {' '.join(cmd)}{NC}")
        
        # Start in background
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(project_root)
        )
        
        # Wait a bit for server to start
        print(f"{YELLOW}Waiting for server to start...{NC}")
        time.sleep(3)
        
        # Check if process is still running
        if process.poll() is None:
            print(f"{GREEN}✅ Server process started (PID: {process.pid}){NC}")
            return True
        else:
            stdout, stderr = process.communicate()
            print(f"{RED}❌ Server failed to start{NC}")
            print(f"{RED}Error: {stderr.decode() if stderr else 'Unknown error'}{NC}")
            return False
            
    except Exception as e:
        print(f"{RED}❌ Failed to start server: {e}{NC}")
        return False


def test_endpoints():
    """Test key endpoints to validate server is working."""
    endpoints = [
        ("/health", "Health check"),
        ("/regime", "Regime endpoint"),
        ("/stats", "Stats endpoint"),
    ]
    
    print(f"\n{BLUE}Testing endpoints...{NC}")
    all_ok = True
    
    for endpoint, name in endpoints:
        try:
            url = f"{API_URL}{endpoint}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    print(f"  {GREEN}✅ {name} ({endpoint}): OK{NC}")
                else:
                    print(f"  {YELLOW}⚠️  {name} ({endpoint}): Status {response.status}{NC}")
                    all_ok = False
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"  {YELLOW}⚠️  {name} ({endpoint}): Not found (404){NC}")
            else:
                print(f"  {RED}❌ {name} ({endpoint}): Error {e.code}{NC}")
                all_ok = False
        except Exception as e:
            print(f"  {RED}❌ {name} ({endpoint}): {e}{NC}")
            all_ok = False
    
    return all_ok


def main():
    """Main function."""
    print("="*60)
    print("FASTAPI SERVER STATUS CHECK")
    print("="*60)
    
    # Check if server is running
    print(f"\n{BLUE}Checking if server is running at {API_URL}...{NC}")
    is_running, message = check_server_running()
    
    if is_running:
        print(f"{GREEN}✅ {message}{NC}")
        
        # Check for process
        has_process, pids = find_api_server_process()
        if has_process:
            print(f"{GREEN}✅ Found server process(es): {', '.join(pids)}{NC}")
        
        # Test endpoints
        endpoints_ok = test_endpoints()
        
        if endpoints_ok:
            print(f"\n{GREEN}✅ Server is running and responding correctly!{NC}")
            print(f"\n{GREEN}Server URL: {API_URL}{NC}")
            print(f"{GREEN}API Docs: {API_URL}/docs{NC}")
            print(f"{GREEN}Health: {API_URL}/health{NC}")
            return 0
        else:
            print(f"\n{YELLOW}⚠️  Server is running but some endpoints may have issues{NC}")
            return 1
    else:
        print(f"{RED}❌ {message}{NC}")
        
        # Check for zombie processes
        has_process, pids = find_api_server_process()
        if has_process:
            print(f"{YELLOW}⚠️  Found process(es) but server not responding: {', '.join(pids)}{NC}")
            print(f"{YELLOW}   You may need to kill these processes first{NC}")
            print(f"{YELLOW}   Run: kill {' '.join(pids)}{NC}")
            return 1
        
        # Ask to start
        print(f"\n{YELLOW}Server is not running.{NC}")
        print(f"{BLUE}Would you like to start it? (y/n): {NC}", end="")
        
        # For automated scripts, auto-start
        response = "y"  # Auto-start for now
        
        if response.lower() == 'y':
            if start_api_server():
                # Wait and check again
                print(f"\n{BLUE}Verifying server started...{NC}")
                time.sleep(2)
                
                is_running, message = check_server_running()
                if is_running:
                    print(f"{GREEN}✅ Server started successfully!{NC}")
                    test_endpoints()
                    print(f"\n{GREEN}Server URL: {API_URL}{NC}")
                    print(f"{GREEN}API Docs: {API_URL}/docs{NC}")
                    return 0
                else:
                    print(f"{RED}❌ Server started but not responding: {message}{NC}")
                    return 1
            else:
                return 1
        else:
            print(f"{YELLOW}Server not started. Exiting.{NC}")
            return 1


if __name__ == "__main__":
    sys.exit(main())

