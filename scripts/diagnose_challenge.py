"""Diagnose why challenge mode is not executing trades."""

import json
import urllib.request
import urllib.parse
from typing import Dict, Optional


def fetch_json(url: str) -> Optional[Dict]:
    """Fetch JSON from URL."""
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"❌ Error fetching {url}: {e}")
        return None


def main():
    """Diagnose challenge mode trading issues."""
    base_url = "http://localhost:8000"
    
    print("=" * 60)
    print("CHALLENGE MODE DIAGNOSTICS")
    print("=" * 60)
    print()
    
    # 1. Check if challenge is running
    print("1️⃣ CHECKING CHALLENGE STATUS")
    print("-" * 60)
    challenge_status = fetch_json(f"{base_url}/challenge/status")
    if not challenge_status:
        print("❌ Challenge mode not started or API not accessible")
        print("   Start challenge with: POST /challenge/start")
        return
    else:
        print(f"✅ Challenge status: {challenge_status.get('status', 'unknown')}")
        print(f"   Current capital: ${challenge_status.get('current_capital', 0):.2f}")
        print(f"   Target capital: ${challenge_status.get('target_capital', 0):.2f}")
        print(f"   Days elapsed: {challenge_status.get('days_elapsed', 0)}")
        print(f"   Days remaining: {challenge_status.get('days_remaining', 0)}")
        
        risk_status = challenge_status.get('risk_status', {})
        if risk_status:
            print(f"   Kill switch: {'🔴 ACTIVE' if risk_status.get('kill_switch_active') else '✅ Inactive'}")
            if risk_status.get('kill_switch_active'):
                print(f"   Kill switch reason: {risk_status.get('kill_switch_reason', 'Unknown')}")
            print(f"   Daily drawdown: {risk_status.get('daily_drawdown_pct', 0):.2f}%")
            print(f"   Trades today: {risk_status.get('trades_today', 0)}")
    
    print()
    
    # 2. Check bot health
    print("2️⃣ CHECKING BOT HEALTH")
    print("-" * 60)
    health = fetch_json(f"{base_url}/health")
    if health:
        print(f"✅ Bot running: {health.get('is_running', False)}")
        print(f"   Bar count: {health.get('bar_count', 0)}")
        print(f"   Error: {health.get('error', 'None')}")
        if health.get('error'):
            print(f"   ⚠️  Bot has error: {health['error']}")
    else:
        print("❌ Could not fetch bot health")
    
    print()
    
    # 3. Check regime status
    print("3️⃣ CHECKING REGIME STATUS")
    print("-" * 60)
    regime = fetch_json(f"{base_url}/regime")
    if regime:
        is_valid = regime.get('is_valid', False)
        confidence = regime.get('confidence', 0.0)
        regime_type = regime.get('regime_type', 'unknown')
        bias = regime.get('bias', 'unknown')
        volatility = regime.get('volatility_level', 'unknown')
        
        print(f"   Regime type: {regime_type}")
        print(f"   Bias: {bias}")
        print(f"   Volatility: {volatility}")
        print(f"   Confidence: {confidence:.2%}")
        print(f"   Is valid: {is_valid}")
        
        # Check if regime meets challenge requirements
        print()
        print("   Challenge Requirements Check:")
        print(f"   - Confidence ≥ 75%: {'✅' if confidence >= 0.75 else '❌'} ({confidence:.2%})")
        print(f"   - Regime is TREND or EXPANSION: {'✅' if regime_type in ['trend', 'expansion'] else '❌'} ({regime_type})")
        print(f"   - Volatility MEDIUM to HIGH: {'✅' if volatility in ['medium', 'high'] else '❌'} ({volatility})")
        print(f"   - Regime is valid: {'✅' if is_valid else '❌'}")
        
        if not is_valid:
            print("   ⚠️  Regime is not valid - waiting for more bars")
        if confidence < 0.75:
            print("   ⚠️  Confidence too low for challenge mode (need ≥75%)")
        if regime_type not in ['trend', 'expansion']:
            print(f"   ⚠️  Regime type '{regime_type}' is blocked in challenge mode")
        if volatility not in ['medium', 'high']:
            print(f"   ⚠️  Volatility '{volatility}' is outside allowed range")
    else:
        print("❌ Could not fetch regime status")
    
    print()
    
    # 4. Check agents
    print("4️⃣ CHECKING AGENTS")
    print("-" * 60)
    agents = fetch_json(f"{base_url}/agents")
    if agents:
        agent_list = agents.get('agents', [])
        print(f"   Total agents: {len(agent_list)}")
        challenge_agents = [a for a in agent_list if 'challenge' in a.get('name', '').lower()]
        if challenge_agents:
            print(f"   ✅ Challenge agents found: {len(challenge_agents)}")
            for agent in challenge_agents:
                print(f"      - {agent.get('name', 'Unknown')}")
        else:
            print("   ⚠️  No challenge agents found - using regular agents?")
    else:
        print("❌ Could not fetch agents")
    
    print()
    
    # 5. Check live status
    print("5️⃣ CHECKING LIVE TRADING STATUS")
    print("-" * 60)
    live_status = fetch_json(f"{base_url}/live/status")
    if live_status:
        print(f"   Mode: {live_status.get('mode', 'unknown')}")
        print(f"   Is running: {live_status.get('is_running', False)}")
        print(f"   Symbols: {live_status.get('symbols', [])}")
        print(f"   Bar count: {live_status.get('bar_count', 0)}")
    else:
        print("❌ Could not fetch live status")
    
    print()
    
    # 6. Summary and recommendations
    print("=" * 60)
    print("DIAGNOSIS SUMMARY")
    print("=" * 60)
    
    issues = []
    recommendations = []
    
    if not challenge_status or challenge_status.get('status') != 'active':
        issues.append("Challenge mode not active")
        recommendations.append("Start challenge mode: POST /challenge/start")
    
    if risk_status and risk_status.get('kill_switch_active'):
        issues.append(f"Kill switch is ACTIVE: {risk_status.get('kill_switch_reason', 'Unknown')}")
        recommendations.append("Review kill switch reason and reset if appropriate")
    
    if regime:
        if not regime.get('is_valid'):
            issues.append("Regime not valid (waiting for bars)")
            recommendations.append("Wait for more bars to be collected (need 30-50 bars)")
        
        if regime.get('confidence', 0) < 0.75:
            issues.append(f"Confidence too low: {regime.get('confidence', 0):.2%} < 75%")
            recommendations.append("Wait for higher confidence regime or check regime engine")
        
        if regime.get('regime_type') not in ['trend', 'expansion']:
            issues.append(f"Regime type '{regime.get('regime_type')}' is blocked")
            recommendations.append("Wait for TREND or EXPANSION regime")
        
        if regime.get('volatility_level') not in ['medium', 'high']:
            issues.append(f"Volatility '{regime.get('volatility_level')}' is outside allowed range")
            recommendations.append("Wait for MEDIUM or HIGH volatility")
    
    if health and health.get('bar_count', 0) < 30:
        issues.append(f"Not enough bars collected: {health.get('bar_count', 0)} < 30")
        recommendations.append("Wait for more bars to be collected")
    
    if issues:
        print("❌ ISSUES FOUND:")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
        print()
        print("💡 RECOMMENDATIONS:")
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. {rec}")
    else:
        print("✅ No obvious issues found")
        print("   If still no trades, check:")
        print("   - Agent confidence thresholds")
        print("   - Controller minimum confidence")
        print("   - Risk manager constraints")
        print("   - Session timing (avoid open/close/choppy hours)")
    
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()

