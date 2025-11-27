#!/usr/bin/env python3
"""Diagnose why trades aren't executing."""

import sys
from pathlib import Path
import json
import urllib.request
import urllib.error

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def main():
    """Diagnose trading issues."""
    base_url = "http://localhost:8000"
    
    print("=" * 60)
    print("TRADING DIAGNOSTICS")
    print("=" * 60)
    
    def fetch_json(url):
        """Fetch JSON from URL using urllib (built-in, no dependencies)."""
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.URLError as e:
            raise Exception(f"Failed to connect to {url}: {e}")
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON response: {e}")
    
    # Check health
    try:
        health = fetch_json(f"{base_url}/health")
        print(f"\n✅ Bot Status: {'Running' if health['is_running'] else 'Stopped'}")
        print(f"✅ Bar Count: {health['bar_count']}")
        print(f"✅ Can Trade: {health['risk_status']['can_trade']}")
        print(f"✅ Kill Switch: {'Engaged' if health['risk_status']['kill_switch_engaged'] else 'Disengaged'}")
    except Exception as e:
        print(f"❌ Error checking health: {e}")
        return
    
    # Check regime
    try:
        regime = fetch_json(f"{base_url}/regime")
        print(f"\n📊 REGIME STATUS:")
        print(f"   Type: {regime.get('regime_type', 'unknown')}")
        print(f"   Confidence: {regime.get('confidence', 0.0):.2f}")
        print(f"   Is Valid: {regime.get('is_valid', False)}")
        print(f"   Bias: {regime.get('bias', 'unknown')}")
        print(f"   Trend: {regime.get('trend_direction', 'unknown')}")
        
        if regime.get('confidence', 0.0) < 0.4:
            print(f"\n⚠️  ISSUE: Regime confidence ({regime.get('confidence', 0.0):.2f}) is below 0.4 threshold!")
            print(f"   → Trades require confidence ≥ 0.4")
    except Exception as e:
        print(f"❌ Error checking regime: {e}")
    
    # Check agents
    try:
        agents = fetch_json(f"{base_url}/agents")
        print(f"\n🤖 AGENTS STATUS:")
        for agent_name, agent_data in agents.items():
            weight = agent_data.get('current_weight', 0.0)
            fitness = agent_data.get('fitness', {})
            print(f"   {agent_name}:")
            print(f"      Weight: {weight:.3f}")
            print(f"      Fitness: {fitness.get('short_term', 0.0):.3f}")
    except Exception as e:
        print(f"❌ Error checking agents: {e}")
    
    # Check recent intents
    try:
        # Try to get recent intents if endpoint exists
        print(f"\n💡 RECOMMENDATIONS:")
        if health['bar_count'] < 50:
            print(f"   ⚠️  Need more bars: {health['bar_count']}/50")
        if regime.get('confidence', 0.0) < 0.4:
            print(f"   ⚠️  Regime confidence too low: {regime.get('confidence', 0.0):.2f}")
            print(f"   → This is the main blocker! Regime needs to classify properly.")
        if not regime.get('is_valid', False):
            print(f"   ⚠️  Regime is not valid")
            print(f"   → Check if features are being computed correctly")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()

