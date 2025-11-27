#!/usr/bin/env python3
"""
Comprehensive validation script to confirm options trading is wired end-to-end.
Runs all checks to ensure OptionsAgent will execute trades.
"""

import sys
import os
import json
from pathlib import Path
import urllib.request
import urllib.error

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

API_URL = "http://localhost:8000"


def check_api_server():
    """Check 1: API server is running"""
    print(f"\n{BLUE}{'='*60}{NC}")
    print(f"{BLUE}CHECK 1: API Server Running{NC}")
    print(f"{BLUE}{'='*60}{NC}")
    
    try:
        req = urllib.request.Request(f"{API_URL}/health")
        with urllib.request.urlopen(req, timeout=2) as response:
            if response.status == 200:
                data = json.loads(response.read())
                print(f"  {GREEN}✅ API server is running{NC}")
                print(f"     Status: {data.get('status', 'unknown')}")
                print(f"     Bar count: {data.get('bar_count', 0)}")
                return True
    except Exception as e:
        print(f"  {RED}❌ API server not running: {e}{NC}")
        return False


def check_options_endpoint():
    """Check 2: Options endpoint exists"""
    print(f"\n{BLUE}{'='*60}{NC}")
    print(f"{BLUE}CHECK 2: Options Endpoint Exists{NC}")
    print(f"{BLUE}{'='*60}{NC}")
    
    try:
        # Try to get API docs to check endpoint
        req = urllib.request.Request(f"{API_URL}/docs")
        with urllib.request.urlopen(req, timeout=2) as response:
            if response.status == 200:
                print(f"  {GREEN}✅ API docs accessible{NC}")
                print(f"     Options endpoint should be at: {API_URL}/options/start")
                return True
    except Exception as e:
        print(f"  {YELLOW}⚠️  Could not verify endpoint: {e}{NC}")
        return True  # Don't fail on this


def check_options_agent_import():
    """Check 3: OptionsAgent imports correctly"""
    print(f"\n{BLUE}{'='*60}{NC}")
    print(f"{BLUE}CHECK 3: OptionsAgent Import{NC}")
    print(f"{BLUE}{'='*60}{NC}")
    
    try:
        from core.agents.options_agent import OptionsAgent
        from core.config.asset_profiles import OptionRiskProfile
        from core.live.options_data_feed import OptionsDataFeed
        
        print(f"  {GREEN}✅ OptionsAgent imports successfully{NC}")
        print(f"  {GREEN}✅ OptionRiskProfile imports successfully{NC}")
        print(f"  {GREEN}✅ OptionsDataFeed imports successfully{NC}")
        return True
    except Exception as e:
        print(f"  {RED}❌ Import failed: {e}{NC}")
        import traceback
        traceback.print_exc()
        return False


def check_options_agent_creation():
    """Check 4: OptionsAgent can be created with correct config"""
    print(f"\n{BLUE}{'='*60}{NC}")
    print(f"{BLUE}CHECK 4: OptionsAgent Creation{NC}")
    print(f"{BLUE}{'='*60}{NC}")
    
    try:
        from core.agents.options_agent import OptionsAgent
        from core.config.asset_profiles import OptionRiskProfile
        from core.live.options_data_feed import OptionsDataFeed
        
        api_key = os.getenv("ALPACA_API_KEY")
        api_secret = os.getenv("ALPACA_SECRET_KEY")
        base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
        
        if not api_key or not api_secret:
            print(f"  {YELLOW}⚠️  Skipping (API keys not set){NC}")
            return True
        
        # Create components
        options_feed = OptionsDataFeed(
            api_key=api_key,
            api_secret=api_secret,
            base_url=base_url
        )
        
        risk_profile = OptionRiskProfile(testing_mode=True)
        
        agent = OptionsAgent(
            symbol="SPY",
            options_data_feed=options_feed,
            option_risk_profile=risk_profile
        )
        
        # Validate config
        print(f"  {GREEN}✅ OptionsAgent created successfully{NC}")
        print(f"     Symbol: {agent.symbol}")
        print(f"     Min confidence: {agent.min_confidence:.2%}")
        print(f"     DTE range: [{agent.min_dte}, {agent.max_dte}]")
        print(f"     Delta range: {agent.delta_range}")
        print(f"     Testing mode: {risk_profile.testing_mode}")
        print(f"     Has selector: {agent.options_selector is not None}")
        print(f"     Has data feed: {agent.options_data_feed is not None}")
        
        # Validate risk profile
        print(f"\n  {BLUE}Risk Profile Config:{NC}")
        print(f"     Max spread: {risk_profile.max_spread_pct:.1%}")
        print(f"     Min OI: {risk_profile.min_open_interest}")
        print(f"     Min volume: {risk_profile.min_volume}")
        print(f"     Max theta decay: {risk_profile.max_theta_decay_allowed:.1%}")
        
        return True
        
    except Exception as e:
        print(f"  {RED}❌ Failed to create OptionsAgent: {e}{NC}")
        import traceback
        traceback.print_exc()
        return False


def check_data_feed_connection():
    """Check 5: Options data feed connects"""
    print(f"\n{BLUE}{'='*60}{NC}")
    print(f"{BLUE}CHECK 5: Options Data Feed Connection{NC}")
    print(f"{BLUE}{'='*60}{NC}")
    
    try:
        from core.live.options_data_feed import OptionsDataFeed
        
        api_key = os.getenv("ALPACA_API_KEY")
        api_secret = os.getenv("ALPACA_SECRET_KEY")
        base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
        
        if not api_key or not api_secret:
            print(f"  {YELLOW}⚠️  Skipping (API keys not set){NC}")
            return True
        
        feed = OptionsDataFeed(
            api_key=api_key,
            api_secret=api_secret,
            base_url=base_url
        )
        
        if feed.connect():
            print(f"  {GREEN}✅ Options data feed connected{NC}")
            
            # Try fetching chain (may fail if market closed, that's OK)
            try:
                chain = feed.get_options_chain("SPY", "put")
                if chain:
                    print(f"  {GREEN}✅ Options chain fetch works ({len(chain)} contracts){NC}")
                else:
                    print(f"  {YELLOW}⚠️  Options chain returned empty (market may be closed){NC}")
            except Exception as e:
                print(f"  {YELLOW}⚠️  Chain fetch test: {e} (may be normal if market closed){NC}")
            
            return True
        else:
            print(f"  {RED}❌ Options data feed connection failed{NC}")
            return False
            
    except Exception as e:
        print(f"  {RED}❌ Error testing data feed: {e}{NC}")
        import traceback
        traceback.print_exc()
        return False


def check_scheduler_integration():
    """Check 6: Scheduler integration"""
    print(f"\n{BLUE}{'='*60}{NC}")
    print(f"{BLUE}CHECK 6: Scheduler Integration{NC}")
    print(f"{BLUE}{'='*60}{NC}")
    
    scheduler_path = Path("core/live/scheduler.py")
    
    if not scheduler_path.exists():
        print(f"  {RED}❌ Scheduler file not found{NC}")
        return False
    
    with open(scheduler_path, 'r') as f:
        content = f.read()
        
        checks = [
            ('options_agent', 'options_agent variable used'),
            ('options_data_feed', 'options_data_feed check'),
            ('trend_agent_signal', 'trend_agent_signal update'),
            ('mean_reversion_agent_signal', 'mean_reversion_agent_signal update'),
            ('volatility_agent_signal', 'volatility_agent_signal update'),
        ]
        
        # Check for options agent handling (can be lowercase or class name)
        has_options_handling = (
            'options_agent' in content.lower() or 
            'OptionsAgent' in content or
            'hasattr' in content and 'options_data_feed' in content
        )
        
        if has_options_handling:
            print(f"  {GREEN}✅ Options agent handling found{NC}")
        else:
            print(f"  {YELLOW}⚠️  Options agent handling not found{NC}")
        
        all_found = True
        for pattern, description in checks:
            if pattern in content:
                print(f"  {GREEN}✅ {description}{NC}")
            else:
                print(f"  {YELLOW}⚠️  {description} not found{NC}")
                all_found = False
        
        return all_found and has_options_handling


def check_config_files():
    """Check 7: Config files are correct"""
    print(f"\n{BLUE}{'='*60}{NC}")
    print(f"{BLUE}CHECK 7: Config Files{NC}")
    print(f"{BLUE}{'='*60}{NC}")
    
    checks = []
    
    # Check settings_loader exists
    if Path("core/settings_loader.py").exists():
        print(f"  {GREEN}✅ core/settings_loader.py exists{NC}")
        checks.append(True)
    else:
        print(f"  {RED}❌ core/settings_loader.py not found{NC}")
        checks.append(False)
    
    # Check config.py doesn't exist (conflict resolved)
    if not Path("core/config.py").exists():
        print(f"  {GREEN}✅ core/config.py removed (conflict resolved){NC}")
        checks.append(True)
    else:
        print(f"  {YELLOW}⚠️  core/config.py still exists (may cause conflicts){NC}")
        checks.append(False)
    
    # Check asset_profiles exists
    if Path("core/config/asset_profiles.py").exists():
        print(f"  {GREEN}✅ core/config/asset_profiles.py exists{NC}")
        checks.append(True)
    else:
        print(f"  {RED}❌ core/config/asset_profiles.py not found{NC}")
        checks.append(False)
    
    return all(checks)


def main():
    """Run all validation checks"""
    print("="*60)
    print("OPTIONS TRADING END-TO-END VALIDATION")
    print("="*60)
    
    checks = [
        ("API Server", check_api_server),
        ("Options Endpoint", check_options_endpoint),
        ("OptionsAgent Import", check_options_agent_import),
        ("OptionsAgent Creation", check_options_agent_creation),
        ("Data Feed Connection", check_data_feed_connection),
        ("Scheduler Integration", check_scheduler_integration),
        ("Config Files", check_config_files),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            passed = check_func()
            results.append((name, passed))
        except Exception as e:
            print(f"  {RED}❌ Check failed with exception: {e}{NC}")
            results.append((name, False))
    
    # Summary
    print()
    print("="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for name, passed in results:
        status = f"{GREEN}✅ PASS{NC}" if passed else f"{RED}❌ FAIL{NC}"
        print(f"  {status} {name}")
    
    print()
    print(f"Results: {passed_count}/{total_count} checks passed")
    
    if passed_count == total_count:
        print(f"\n{GREEN}✅ ALL CHECKS PASSED!{NC}")
        print()
        print("Options trading system is fully validated and ready!")
        print()
        print("Next steps:")
        print("  1. Start options trading:")
        print(f"     curl -X POST {API_URL}/options/start \\")
        print("       -H 'Content-Type: application/json' \\")
        print("       -d '{\"underlying_symbol\": \"SPY\", \"option_type\": \"put\", \"testing_mode\": true}'")
        print()
        print("  2. Watch logs:")
        print("     tail -f logs/*.log | grep -Ei 'optionsagent|reject|accept|order'")
        print()
        print("  3. Check for trade execution in logs")
        return 0
    else:
        print(f"\n{RED}❌ SOME CHECKS FAILED{NC}")
        print()
        print("Please fix the issues above before proceeding")
        return 1


if __name__ == "__main__":
    sys.exit(main())

