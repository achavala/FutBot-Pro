#!/usr/bin/env python3
"""
Comprehensive diagnostic script to verify all trading components are working.
Shows the complete decision flow from bar → features → regime → agents → controller → execution.
"""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from datetime import datetime


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def get_json(url: str):
    """Get JSON from API endpoint."""
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}


def print_dict(data: dict, indent: int = 0):
    """Pretty print dictionary."""
    for key, value in data.items():
        prefix = "  " * indent
        if isinstance(value, dict):
            print(f"{prefix}{key}:")
            print_dict(value, indent + 1)
        elif isinstance(value, list):
            print(f"{prefix}{key}: [{len(value)} items]")
            if value and isinstance(value[0], dict):
                for i, item in enumerate(value[:3]):  # Show first 3
                    print(f"{prefix}  [{i}]:")
                    print_dict(item, indent + 2)
        else:
            print(f"{prefix}{key}: {value}")


def main():
    base_url = "http://localhost:8000"
    
    print_section("FutBot Trading Flow Diagnostic")
    print(f"Time: {datetime.now().isoformat()}")
    print()
    
    # 1. Check if bot is running
    print_section("1. Bot Status")
    status = get_json(f"{base_url}/live/status")
    if status is None or "error" in status:
        error_msg = status.get("error", "Unknown error") if status else "No response"
        print(f"❌ Cannot connect to bot: {error_msg}")
        print("   Make sure the API server is running: python main.py --mode api")
        return
    print_dict(status)
    
    if not status.get("is_running"):
        print("\n⚠️  Bot is not running. Start it with: POST /live/start")
        return
    
    bar_count = status.get("bar_count", 0)
    if bar_count < 50:
        print(f"\n⚠️  Only {bar_count} bars collected. Need 50+ bars before trading starts.")
        print("   The bot is collecting data. Trades will begin automatically at 50+ bars.")
    
    print()
    
    # 2. Check portfolio and stats
    print_section("2. Portfolio & Trading Stats")
    stats = get_json(f"{base_url}/stats")
    print_dict(stats)
    
    total_trades = stats.get("total_trades", 0)
    if total_trades == 0:
        print("\n📊 No trades executed yet.")
        if bar_count < 50:
            print("   Reason: Still collecting bars (< 50)")
        else:
            print("   Reason: Waiting for valid signals or risk approval")
    else:
        print(f"\n✅ {total_trades} trades executed")
    
    print()
    
    # 3. Check risk manager
    print_section("3. Risk Manager Status")
    risk = get_json(f"{base_url}/risk-status")
    print_dict(risk)
    
    can_trade = risk.get("can_trade", False)
    kill_switch = risk.get("kill_switch_engaged", False)
    
    if kill_switch:
        print("\n🚨 KILL SWITCH ENGAGED - Trading is disabled")
    elif not can_trade:
        print("\n⚠️  Risk manager says trading is not allowed")
    else:
        print("\n✅ Risk manager allows trading")
    
    print()
    
    # 4. Check regime (if available)
    print_section("4. Current Regime Classification")
    regime = get_json(f"{base_url}/regime")
    if "error" in regime or "detail" in regime:
        print("⚠️  No regime data available yet")
        print("   This is normal until 50+ bars are collected")
    else:
        print_dict(regime)
        print("\n✅ Regime engine is working")
    
    print()
    
    # 5. Check agent fitness
    print_section("5. Agent Fitness & Weights")
    agents = get_json(f"{base_url}/agents")
    if agents:
        print_dict(agents)
        print("\n✅ Agents are initialized")
    else:
        print("⚠️  No agent data available")
    
    print()
    
    # 6. Check recent events/logs
    print_section("6. Recent Trading Events")
    try:
        log_file = Path("logs/trading_events.jsonl")
        if log_file.exists():
            lines = log_file.read_text().strip().split("\n")
            recent = lines[-10:] if len(lines) > 10 else lines
            print(f"Showing last {len(recent)} events:")
            for line in recent:
                if line.strip():
                    try:
                        event = json.loads(line)
                        event_type = event.get("event_type", "unknown")
                        timestamp = event.get("timestamp", "")[:19]  # Truncate microseconds
                        print(f"  [{timestamp}] {event_type}: {event.get('reason', event.get('message', ''))}")
                    except:
                        print(f"  {line[:80]}...")
        else:
            print("⚠️  No log file found at logs/trading_events.jsonl")
    except Exception as e:
        print(f"⚠️  Error reading logs: {e}")
    
    print()
    
    # 7. Trading Decision Flow Summary
    print_section("7. Trading Decision Flow Status")
    
    flow_checks = {
        "Data Collection": bar_count >= 50,
        "Feature Computation": bar_count >= 50,
        "Regime Classification": "regime" in locals() and "error" not in regime,
        "Agent Evaluation": "agents" in locals() and bool(agents),
        "Risk Approval": can_trade and not kill_switch,
        "Execution Ready": bar_count >= 50 and can_trade and not kill_switch,
    }
    
    for check, passed in flow_checks.items():
        status_icon = "✅" if passed else "⏳"
        print(f"  {status_icon} {check}: {'Ready' if passed else 'Waiting'}")
    
    print()
    
    # 8. Recommendations
    print_section("8. Recommendations")
    
    if bar_count < 50:
        print("📌 Wait for more bars to accumulate (need 50+)")
        print("   Current:", bar_count, "bars")
        print("   Estimated time:", max(0, 50 - bar_count), "minutes")
    
    if kill_switch:
        print("📌 Disengage kill switch: POST /kill-switch/disengage")
    
    if not can_trade and not kill_switch:
        print("📌 Check risk constraints - may be hitting limits")
    
    if bar_count >= 50 and can_trade and total_trades == 0:
        print("📌 Bot is ready but no trades yet. Possible reasons:")
        print("   - Regime confidence too low")
        print("   - No valid agent signals")
        print("   - Market conditions not favorable")
        print("   - Check logs for 'no trade' events")
    
    print()
    print("=" * 60)
    print("Diagnostic complete. Monitor with: ./scripts/monitor_bot.sh")
    print("=" * 60)


if __name__ == "__main__":
    main()

