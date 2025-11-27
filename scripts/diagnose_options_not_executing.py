#!/usr/bin/env python3
"""
Quick diagnostic to identify why options trading is not executing.
Runs checks without needing historical data.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Colors
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'


def check_1_environment():
    """Check 1: Environment variables"""
    print(f"\n{BLUE}{'='*60}{NC}")
    print(f"{BLUE}CHECK 1: Environment Variables{NC}")
    print(f"{BLUE}{'='*60}{NC}")
    
    issues = []
    
    api_key = os.getenv("ALPACA_API_KEY")
    api_secret = os.getenv("ALPACA_SECRET_KEY")
    
    if not api_key:
        issues.append("ALPACA_API_KEY not set")
        print(f"  {RED}❌ ALPACA_API_KEY not set{NC}")
    else:
        print(f"  {GREEN}✅ ALPACA_API_KEY set{NC}")
    
    if not api_secret:
        issues.append("ALPACA_SECRET_KEY not set")
        print(f"  {RED}❌ ALPACA_SECRET_KEY not set{NC}")
    else:
        print(f"  {GREEN}✅ ALPACA_SECRET_KEY set{NC}")
    
    return len(issues) == 0, issues


def check_options_agent_import():
    """Check 2: OptionsAgent can be imported"""
    print(f"\n{BLUE}{'='*60}{NC}")
    print(f"{BLUE}CHECK 2: OptionsAgent Import{NC}")
    print(f"{BLUE}{'='*60}{NC}")
    
    try:
        from core.agents.options_agent import OptionsAgent
        print(f"  {GREEN}✅ OptionsAgent imported successfully{NC}")
        return True, []
    except Exception as e:
        print(f"  {RED}❌ Failed to import OptionsAgent: {e}{NC}")
        return False, [f"Import error: {e}"]


def check_3_options_data_feed():
    """Check 3: Options data feed connection"""
    print(f"\n{BLUE}{'='*60}{NC}")
    print(f"{BLUE}CHECK 3: Options Data Feed Connection{NC}")
    print(f"{BLUE}{'='*60}{NC}")
    
    try:
        from core.live.options_data_feed import OptionsDataFeed
        
        api_key = os.getenv("ALPACA_API_KEY")
        api_secret = os.getenv("ALPACA_SECRET_KEY")
        base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
        
        if not api_key or not api_secret:
            print(f"  {YELLOW}⚠️  Skipping (API keys not set){NC}")
            return True, []
        
        feed = OptionsDataFeed(
            api_key=api_key,
            api_secret=api_secret,
            base_url=base_url
        )
        
        if feed.connect():
            print(f"  {GREEN}✅ Options data feed connected{NC}")
            
            # Try to fetch a chain
            try:
                chain = feed.get_options_chain("SPY", "put")
                if chain:
                    print(f"  {GREEN}✅ Options chain fetch works ({len(chain)} contracts){NC}")
                else:
                    print(f"  {YELLOW}⚠️  Options chain fetch returned empty{NC}")
            except Exception as e:
                print(f"  {YELLOW}⚠️  Options chain fetch failed: {e}{NC}")
            
            return True, []
        else:
            print(f"  {RED}❌ Options data feed connection failed{NC}")
            return False, ["Options data feed connection failed"]
            
    except Exception as e:
        print(f"  {RED}❌ Error testing options data feed: {e}{NC}")
        import traceback
        traceback.print_exc()
        return False, [f"Error: {e}"]


def check_4_options_agent_creation():
    """Check 4: OptionsAgent can be created"""
    print(f"\n{BLUE}{'='*60}{NC}")
    print(f"{BLUE}CHECK 4: OptionsAgent Creation{NC}")
    print(f"{BLUE}{'='*60}{NC}")
    
    try:
        from core.agents.options_agent import OptionsAgent
        from core.live.options_data_feed import OptionsDataFeed
        from core.config.asset_profiles import OptionRiskProfile
        
        api_key = os.getenv("ALPACA_API_KEY")
        api_secret = os.getenv("ALPACA_SECRET_KEY")
        base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
        
        if not api_key or not api_secret:
            print(f"  {YELLOW}⚠️  Skipping (API keys not set){NC}")
            return True, []
        
        # Create options feed
        options_feed = OptionsDataFeed(
            api_key=api_key,
            api_secret=api_secret,
            base_url=base_url
        )
        
        # Create risk profile
        risk_profile = OptionRiskProfile(testing_mode=True)
        
        # Create agent
        agent = OptionsAgent(
            symbol="SPY",
            options_data_feed=options_feed,
            option_risk_profile=risk_profile
        )
        
        print(f"  {GREEN}✅ OptionsAgent created successfully{NC}")
        print(f"     Symbol: {agent.symbol}")
        print(f"     Has data feed: {agent.options_data_feed is not None}")
        print(f"     Has risk profile: {agent.option_risk_profile is not None}")
        print(f"     Min confidence: {agent.min_confidence}")
        
        return True, []
        
    except Exception as e:
        print(f"  {RED}❌ Failed to create OptionsAgent: {e}{NC}")
        import traceback
        traceback.print_exc()
        return False, [f"Error: {e}"]


def check_5_fastapi_endpoint():
    """Check 5: FastAPI endpoint exists"""
    print(f"\n{BLUE}{'='*60}{NC}")
    print(f"{BLUE}CHECK 5: FastAPI Endpoint{NC}")
    print(f"{BLUE}{'='*60}{NC}")
    
    try:
        import importlib.util
        fastapi_path = Path("ui/fastapi_app.py")
        
        if not fastapi_path.exists():
            print(f"  {RED}❌ FastAPI app not found{NC}")
            return False, ["FastAPI app file not found"]
        
        # Check if endpoint exists
        with open(fastapi_path, 'r') as f:
            content = f.read()
            if '/options/start' in content:
                print(f"  {GREEN}✅ /options/start endpoint exists{NC}")
            else:
                print(f"  {RED}❌ /options/start endpoint not found{NC}")
                return False, ["Endpoint not found"]
            
            if 'OptionsAgent' in content:
                print(f"  {GREEN}✅ OptionsAgent referenced in FastAPI{NC}")
            else:
                print(f"  {YELLOW}⚠️  OptionsAgent not referenced in FastAPI{NC}")
        
        return True, []
        
    except Exception as e:
        print(f"  {RED}❌ Error checking FastAPI: {e}{NC}")
        return False, [f"Error: {e}"]


def check_6_scheduler_integration():
    """Check 6: Scheduler integration"""
    print(f"\n{BLUE}{'='*60}{NC}")
    print(f"{BLUE}CHECK 6: Scheduler Integration{NC}")
    print(f"{BLUE}{'='*60}{NC}")
    
    try:
        scheduler_path = Path("core/live/scheduler.py")
        
        if not scheduler_path.exists():
            print(f"  {RED}❌ Scheduler file not found{NC}")
            return False, ["Scheduler file not found"]
        
        with open(scheduler_path, 'r') as f:
            content = f.read()
            if 'OptionsAgent' in content or 'options_agent' in content:
                print(f"  {GREEN}✅ Scheduler references OptionsAgent{NC}")
            else:
                print(f"  {YELLOW}⚠️  OptionsAgent not found in scheduler{NC}")
        
        return True, []
        
    except Exception as e:
        print(f"  {RED}❌ Error checking scheduler: {e}{NC}")
        return False, [f"Error: {e}"]


def main():
    """Run all checks"""
    print("="*60)
    print("OPTIONS TRADING DIAGNOSTIC")
    print("="*60)
    
    print("Running diagnostic checks...")
    print()
    
    all_checks = [
        ("Environment Variables", check_1_environment),
        ("OptionsAgent Import", check_options_agent_import),
        ("Options Data Feed", check_3_options_data_feed),
        ("OptionsAgent Creation", check_4_options_agent_creation),
        ("FastAPI Endpoint", check_5_fastapi_endpoint),
        ("Scheduler Integration", check_6_scheduler_integration),
    ]
    
    results = []
    all_passed = True
    for name, check_func in all_checks:
        passed, issues = check_func()
        if not passed:
            all_passed = False
    
    # Summary
    print()
    print("="*60)
    print("DIAGNOSTIC SUMMARY")
    print("="*60)
    
    if all_passed:
        print(f"{GREEN}✅ All checks passed!{NC}")
        print()
        print("System appears to be configured correctly.")
        print()
        print("Next steps:")
        print("  1. Start options trading via FastAPI: POST /options/start")
        print("  2. Check logs for OptionsAgent evaluation")
    else:
        print(f"{RED}❌ Some checks failed{NC}")
        print()
        print("Please fix the issues above before proceeding")
        print("  2. Check logs for detailed error messages")
    
    print()
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

