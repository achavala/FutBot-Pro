"""Comprehensive diagnostic for why no trades are executing."""

import json
import urllib.request
from datetime import datetime


def fetch_json(url: str):
    """Fetch JSON from URL."""
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        return {"error": str(e)}


def main():
    """Diagnose why no trades are executing."""
    base_url = "http://localhost:8000"
    
    print("=" * 70)
    print("COMPREHENSIVE NO-TRADES DIAGNOSTIC")
    print("=" * 70)
    print()
    
    # 1. Check if bot is running
    print("1️⃣ BOT STATUS")
    print("-" * 70)
    health = fetch_json(f"{base_url}/health")
    if health.get("error"):
        print(f"❌ Cannot connect to API: {health['error']}")
        print("   Is the API server running?")
        return
    
    is_running = health.get("is_running", False)
    bar_count = health.get("bar_count", 0)
    error = health.get("error")
    
    print(f"   Bot running: {'✅ YES' if is_running else '❌ NO'}")
    print(f"   Bar count: {bar_count}")
    if error:
        print(f"   ⚠️  Error: {error}")
    
    if not is_running:
        print()
        print("   💡 SOLUTION: Start the bot first:")
        print("      curl -X POST http://localhost:8000/live/start \\")
        print("        -H 'Content-Type: application/json' \\")
        print("        -d '{\"symbols\": [\"QQQ\"], \"broker_type\": \"alpaca\"}'")
        return
    
    if bar_count < 30:
        print(f"   ⚠️  Not enough bars: {bar_count} < 30 (need at least 30)")
        print("   💡 Wait for more bars to be collected")
    
    print()
    
    # 2. Check regime
    print("2️⃣ REGIME ANALYSIS")
    print("-" * 70)
    regime = fetch_json(f"{base_url}/regime")
    if regime and not regime.get("error"):
        is_valid = regime.get("is_valid", False)
        confidence = regime.get("confidence", 0.0)
        regime_type = regime.get("regime_type", "unknown")
        bias = regime.get("bias", "unknown")
        volatility = regime.get("volatility_level", "unknown")
        
        print(f"   Regime type: {regime_type}")
        print(f"   Bias: {bias}")
        print(f"   Volatility: {volatility}")
        print(f"   Confidence: {confidence:.2%}")
        print(f"   Is valid: {'✅' if is_valid else '❌'}")
        
        print()
        print("   Challenge Mode Requirements:")
        print(f"   - Confidence ≥ 75%: {'✅' if confidence >= 0.75 else '❌'} ({confidence:.2%})")
        print(f"   - Regime TREND/EXPANSION: {'✅' if regime_type in ['trend', 'expansion'] else '❌'} ({regime_type})")
        print(f"   - Volatility MEDIUM/HIGH: {'✅' if volatility in ['medium', 'high'] else '❌'} ({volatility})")
        print(f"   - Regime valid: {'✅' if is_valid else '❌'}")
        
        if not is_valid:
            print("   ⚠️  Regime not valid - need more bars")
        if confidence < 0.75:
            print(f"   ⚠️  Confidence {confidence:.2%} < 75% (challenge mode requirement)")
        if regime_type not in ['trend', 'expansion']:
            print(f"   ⚠️  Regime '{regime_type}' is blocked in challenge mode")
        if volatility not in ['medium', 'high']:
            print(f"   ⚠️  Volatility '{volatility}' outside allowed range")
    else:
        print("   ❌ Could not fetch regime")
    
    print()
    
    # 3. Check agents
    print("3️⃣ AGENT STATUS")
    print("-" * 70)
    agents = fetch_json(f"{base_url}/agents")
    if agents and not agents.get("error"):
        agent_list = agents.get("agents", [])
        print(f"   Total agents: {len(agent_list)}")
        
        # Handle both dict and list formats
        if isinstance(agent_list, dict):
            agent_list = list(agent_list.values())
        challenge_agents = [a for a in agent_list if isinstance(a, dict) and 'challenge' in a.get('name', '').lower()]
        if challenge_agents:
            print(f"   ✅ Challenge agents: {len(challenge_agents)}")
        else:
            print("   ⚠️  No challenge agents found")
            print("   💡 If using challenge mode, ensure challenge agents are loaded")
        
        for agent in agent_list[:5]:  # Show first 5
            name = agent.get('name', 'Unknown')
            symbol = agent.get('symbol', 'N/A')
            print(f"      - {name} ({symbol})")
    else:
        print("   ❌ Could not fetch agents")
    
    print()
    
    # 4. Check live status
    print("4️⃣ LIVE TRADING STATUS")
    print("-" * 70)
    live_status = fetch_json(f"{base_url}/live/status")
    if live_status and not live_status.get("error"):
        mode = live_status.get("mode", "unknown")
        symbols = live_status.get("symbols", [])
        broker = live_status.get("broker_type", "unknown")
        
        print(f"   Mode: {mode}")
        print(f"   Symbols: {symbols}")
        print(f"   Broker: {broker}")
        print(f"   Bar count: {live_status.get('bar_count', 0)}")
    else:
        print("   ❌ Could not fetch live status")
    
    print()
    
    # 5. Check recent trades
    print("5️⃣ RECENT TRADES")
    print("-" * 70)
    stats = fetch_json(f"{base_url}/stats")
    if stats and not stats.get("error"):
        trades = stats.get("recent_trades", [])
        print(f"   Recent trades: {len(trades)}")
        if trades:
            for trade in trades[:5]:
                print(f"      - {trade.get('symbol', 'N/A')}: {trade.get('side', 'N/A')} @ ${trade.get('price', 0):.2f}")
        else:
            print("   ⚠️  No trades executed yet")
    else:
        print("   ⚠️  Could not fetch trade stats")
    
    print()
    
    # 6. Root cause analysis
    print("=" * 70)
    print("ROOT CAUSE ANALYSIS")
    print("=" * 70)
    print()
    
    issues = []
    solutions = []
    
    # Check bar count
    if bar_count < 30:
        issues.append(f"Insufficient bars: {bar_count} < 30")
        solutions.append("Wait for more bars to be collected (need 30+ for feature computation)")
    
    # Check regime validity
    if regime and not regime.get("error"):
        if not regime.get("is_valid"):
            issues.append("Regime not valid (waiting for bars)")
            solutions.append("Wait for regime to become valid (need 30+ bars)")
        
        confidence = regime.get("confidence", 0.0)
        if confidence < 0.75:
            issues.append(f"Confidence too low: {confidence:.2%} < 75%")
            solutions.append("Wait for higher confidence regime OR lower challenge mode threshold")
        
        regime_type = regime.get("regime_type", "")
        if regime_type not in ['trend', 'expansion']:
            issues.append(f"Regime '{regime_type}' is blocked in challenge mode")
            solutions.append("Wait for TREND or EXPANSION regime")
        
        volatility = regime.get("volatility_level", "")
        if volatility not in ['medium', 'high']:
            issues.append(f"Volatility '{volatility}' outside allowed range")
            solutions.append("Wait for MEDIUM or HIGH volatility")
    
    # Check if challenge mode is active
    challenge_status = fetch_json(f"{base_url}/challenge/status")
    if challenge_status and not challenge_status.get("error"):
        risk_status = challenge_status.get("risk_status", {})
        if risk_status.get("kill_switch_active"):
            issues.append(f"Kill switch ACTIVE: {risk_status.get('kill_switch_reason', 'Unknown')}")
            solutions.append("Review kill switch reason and reset if appropriate")
    else:
        issues.append("Challenge mode not started (if using challenge mode)")
        solutions.append("Start challenge mode: POST /challenge/start")
    
    if issues:
        print("❌ ISSUES FOUND:")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
        print()
        print("💡 SOLUTIONS:")
        for i, solution in enumerate(solutions, 1):
            print(f"   {i}. {solution}")
    else:
        print("✅ No obvious blocking issues found")
        print()
        print("   Possible reasons:")
        print("   1. Session timing (avoiding open/close/choppy hours)")
        print("   2. Agent confidence thresholds too high")
        print("   3. Controller minimum confidence blocking")
        print("   4. Risk manager constraints")
        print("   5. Market conditions not favorable")
        print()
        print("   💡 Check logs for detailed agent/controller decisions")
    
    print()
    print("=" * 70)
    print("QUICK FIXES")
    print("=" * 70)
    print()
    print("If you want to see trades faster (for testing):")
    print()
    print("1. Lower challenge mode confidence threshold:")
    print("   Edit: core/live/challenge_risk_manager.py")
    print("   Change: min_confidence_for_trade = 0.60  # Lower from 0.75")
    print()
    print("2. Allow more regime types (for testing):")
    print("   Edit: ui/fastapi_app.py (challenge start)")
    print("   Change: allowed_regimes to include MEAN_REVERSION")
    print()
    print("3. Disable session filters (for testing):")
    print("   Set: avoid_choppy_hours=False, avoid_market_open_close=False")
    print()
    print("4. Check if regular trading (non-challenge) works:")
    print("   curl -X POST http://localhost:8000/live/start \\")
    print("     -H 'Content-Type: application/json' \\")
    print("     -d '{\"symbols\": [\"QQQ\"], \"broker_type\": \"alpaca\"}'")
    print()


if __name__ == "__main__":
    main()

