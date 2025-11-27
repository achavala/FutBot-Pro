#!/usr/bin/env python3
"""
3-Layer Diagnostic Plan for Options Trading Pipeline
Goal: Get at least one options trade to execute end-to-end in testing mode

This script provides a methodical diagnostic approach:
1. Execution plane - broker & order path
2. Data plane - options chain / quotes / Greeks
3. Decision plane - agents, filters, selector, scheduler
"""

import json
import sys
import time
import requests
from typing import Dict, Optional

# ==========================================
# CONFIGURATION (Edit only here)
# ==========================================
API_BASE = "http://localhost:8000"
TEST_SYMBOL = "SPY"
TEST_OPTION_SYMBOL = None  # Will be fetched from chain
ENV = "paper"  # "paper" or "live"
TIMEOUT = 10  # seconds

def get_real_option_symbol() -> Optional[str]:
    """Get a real option symbol from the chain."""
    try:
        resp = requests.get(
            f"{API_BASE}/options/chain",
            params={"symbol": TEST_SYMBOL, "option_type": "put"},
            timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            chain = resp.json()
            if isinstance(chain, list) and len(chain) > 0:
                return chain[0].get("symbol")
            elif isinstance(chain, dict):
                contracts = chain.get("contracts", chain.get("chain", []))
                if contracts:
                    return contracts[0].get("symbol")
    except:
        pass
    return None

# ==========================================
# LAYER 1: EXECUTION PLANE
# ==========================================
def run_layer_1_execution() -> Dict:
    """Test force_buy → BrokerClient → Broker."""
    result = {
        "layer": "execution",
        "status": "UNKNOWN",
        "case": None,
        "details": "",
    }
    
    # Get a real option symbol first
    option_symbol = TEST_OPTION_SYMBOL or get_real_option_symbol()
    if not option_symbol:
        result["status"] = "SKIP"
        result["case"] = "NO_SYMBOL"
        result["details"] = "Cannot get option symbol from chain - skipping execution test"
        return result
    
    try:
        resp = requests.post(
            f"{API_BASE}/options/force_buy",
            json={"option_symbol": option_symbol, "qty": 1},
            timeout=TIMEOUT,
        )
    except requests.exceptions.RequestException as e:
        result["status"] = "FAIL"
        result["case"] = "CASE_C"
        result["details"] = f"Force buy request failed: {e}"
        return result
    
    if resp.status_code != 200:
        result["status"] = "FAIL"
        result["case"] = "CASE_B"
        result["details"] = f"HTTP {resp.status_code}: {resp.text[:500]}"
        return result
    
    try:
        data = resp.json()
    except json.JSONDecodeError:
        result["status"] = "FAIL"
        result["case"] = "CASE_B"
        result["details"] = f"Invalid JSON response: {resp.text[:500]}"
        return result
    
    # Check for successful order submission
    if data.get("status") in ("submitted", "accepted", "filled", "pending"):
        result["status"] = "PASS"
        result["case"] = "CASE_A"
        result["details"] = f"Broker accepted order: {data.get('order_id', 'N/A')}"
    elif "error" in data or "failed" in str(data).lower():
        result["status"] = "FAIL"
        result["case"] = "CASE_B"
        result["details"] = f"Broker rejected: {data.get('detail', data.get('error', str(data)))}"
    else:
        result["status"] = "FAIL"
        result["case"] = "CASE_B"
        result["details"] = f"Unknown response: {data}"
    
    return result


# ==========================================
# LAYER 2: DATA PLANE
# ==========================================
def run_layer_2_data() -> Dict:
    """Test options chain + quotes/Greeks availability."""
    result = {
        "layer": "data",
        "status": "UNKNOWN",
        "case": None,
        "details": "",
    }
    
    # 1) Test chain fetch
    try:
        resp = requests.get(
            f"{API_BASE}/options/chain",
            params={"symbol": TEST_SYMBOL, "option_type": "put"},
            timeout=TIMEOUT,
        )
    except requests.exceptions.RequestException as e:
        result["status"] = "FAIL"
        result["case"] = "CASE_D"
        result["details"] = f"Chain request failed: {e}"
        return result
    
    if resp.status_code != 200:
        result["status"] = "FAIL"
        result["case"] = "CASE_D"
        result["details"] = f"Chain HTTP {resp.status_code}: {resp.text[:500]}"
        return result
    
    try:
        chain = resp.json()
        # Handle both list and dict responses
        if isinstance(chain, list):
            contract_count = len(chain)
        elif isinstance(chain, dict):
            contract_count = len(chain.get("contracts", chain.get("chain", [])))
        else:
            contract_count = 0
    except (json.JSONDecodeError, AttributeError):
        result["status"] = "FAIL"
        result["case"] = "CASE_D"
        result["details"] = f"Invalid chain response: {resp.text[:500]}"
        return result
    
    if contract_count == 0:
        result["status"] = "FAIL"
        result["case"] = "CASE_D"
        result["details"] = f"Chain returned 0 contracts for {TEST_SYMBOL}"
        return result
    
    # 2) Test quotes/Greeks for a sample contract
    # Get first contract symbol from chain
    if isinstance(chain, list) and len(chain) > 0:
        sample_contract = chain[0].get("symbol", TEST_OPTION_SYMBOL)
    elif isinstance(chain, dict):
        contracts = chain.get("contracts", chain.get("chain", []))
        if contracts:
            sample_contract = contracts[0].get("symbol", TEST_OPTION_SYMBOL)
        else:
            sample_contract = TEST_OPTION_SYMBOL
    else:
        sample_contract = TEST_OPTION_SYMBOL
    
    try:
        quote_resp = requests.get(
            f"{API_BASE}/options/quote",
            params={"option_symbol": sample_contract},
            timeout=TIMEOUT,
        )
    except requests.exceptions.RequestException as e:
        result["status"] = "FAIL"
        result["case"] = "CASE_E"
        result["details"] = f"Quote request failed: {e}"
        return result
    
    if quote_resp.status_code != 200:
        result["status"] = "FAIL"
        result["case"] = "CASE_E"
        result["details"] = f"Quote HTTP {quote_resp.status_code}: {quote_resp.text[:500]}"
        return result
    
    try:
        quote_data = quote_resp.json()
        has_quote = bool(quote_data.get("bid") or quote_data.get("ask") or quote_data.get("mid"))
    except (json.JSONDecodeError, AttributeError):
        result["status"] = "FAIL"
        result["case"] = "CASE_E"
        result["details"] = f"Invalid quote response: {quote_resp.text[:500]}"
        return result
    
    if not has_quote:
        result["status"] = "FAIL"
        result["case"] = "CASE_E"
        result["details"] = f"Quote response missing bid/ask/mid for {sample_contract}"
        return result
    
    result["status"] = "PASS"
    result["case"] = "OK"
    result["details"] = f"Chain={contract_count} contracts, Quote OK for {sample_contract}"
    return result


# ==========================================
# LAYER 3: DECISION PLANE
# ==========================================
def run_layer_3_decision() -> Dict:
    """Test full decision pipeline in testing mode."""
    result = {
        "layer": "decision",
        "status": "UNKNOWN",
        "case": None,
        "details": "",
    }
    
    # Start options trading in testing mode
    try:
        resp = requests.post(
            f"{API_BASE}/options/start",
            json={
                "underlying_symbol": TEST_SYMBOL,
                "option_type": "put",
                "testing_mode": True
            },
            timeout=TIMEOUT,
        )
    except requests.exceptions.RequestException as e:
        result["status"] = "FAIL"
        result["case"] = "CASE_F"
        result["details"] = f"/options/start failed: {e}"
        return result
    
    if resp.status_code != 200:
        result["status"] = "FAIL"
        result["case"] = "CASE_F"
        result["details"] = f"/options/start HTTP {resp.status_code}: {resp.text[:500]}"
        return result
    
    # Wait for scheduler to process a few ticks
    print(f"  Waiting 5 seconds for scheduler to process...", end="", flush=True)
    time.sleep(5)
    print(" done")
    
    # Try to get status/diagnostic info
    # Option 1: Check if there's a status endpoint
    try:
        status_resp = requests.get(
            f"{API_BASE}/options/positions",
            timeout=TIMEOUT,
        )
        # If positions endpoint exists, we can infer some state
        if status_resp.status_code == 200:
            positions = status_resp.json().get("positions", [])
            if positions:
                result["status"] = "PASS"
                result["case"] = "OK"
                result["details"] = f"Options trading active, {len(positions)} positions"
                return result
    except:
        pass
    
    # Option 2: Check agents endpoint to see if OptionsAgent is registered
    try:
        agents_resp = requests.get(f"{API_BASE}/agents", timeout=TIMEOUT)
        if agents_resp.status_code == 200:
            agents = agents_resp.json()
            agent_names = [a.get("name", "") if isinstance(a, dict) else str(a) for a in agents]
            has_options_agent = any("options" in name.lower() for name in agent_names)
            
            if not has_options_agent:
                result["status"] = "FAIL"
                result["case"] = "CASE_F"
                result["details"] = "OptionsAgent not found in agents list"
                return result
    except:
        pass
    
    # Since we can't easily get real-time stats, we'll indicate manual log checking needed
    result["status"] = "UNKNOWN"
    result["case"] = "MANUAL_CHECK"
    result["details"] = (
        f"Options trading started. Check logs for: "
        f"CandidatesEvaluated, CandidatesPassed, ACCEPT, SubmittingOrder. "
        f"Run: tail -f logs/*.log | grep -i 'optionsagent'"
    )
    
    return result


# ==========================================
# MAIN
# ==========================================
def main():
    """Run the 3-layer diagnostic."""
    print("=" * 60)
    print("OPTIONS PIPELINE DIAGNOSTIC")
    print("=" * 60)
    print(f"API: {API_BASE}")
    print(f"Symbol: {TEST_SYMBOL}")
    option_symbol = TEST_OPTION_SYMBOL or get_real_option_symbol()
    print(f"Option: {option_symbol or '(will fetch from chain)'}")
    print(f"Env: {ENV}")
    print()
    
    results = []
    
    # Run layers in order
    print("[LAYER 1] Testing execution plane...")
    results.append(run_layer_1_execution())
    
    print(f"[LAYER 1] {results[-1]['status']} ({results[-1]['case']}): {results[-1]['details']}")
    print()
    
    # Stop if execution plane fails
    if results[-1]["status"] != "PASS":
        print("⚠️  Execution plane failed. Fix broker connectivity before proceeding.")
        print()
        print_summary(results)
        sys.exit(1)
    
    print("[LAYER 2] Testing data plane...")
    results.append(run_layer_2_data())
    
    print(f"[LAYER 2] {results[-1]['status']} ({results[-1]['case']}): {results[-1]['details']}")
    print()
    
    # Stop if data plane fails
    if results[-1]["status"] != "PASS":
        print("⚠️  Data plane failed. Fix data feed before proceeding.")
        print()
        print_summary(results)
        sys.exit(2)
    
    print("[LAYER 3] Testing decision plane...")
    results.append(run_layer_3_decision())
    
    print(f"[LAYER 3] {results[-1]['status']} ({results[-1]['case']}): {results[-1]['details']}")
    print()
    
    # Print summary
    print_summary(results)
    
    # Exit code: 0 if all PASS, otherwise layer-specific code
    if all(r["status"] == "PASS" for r in results):
        sys.exit(0)
    elif results[0]["status"] != "PASS":
        sys.exit(1)  # Execution plane failure
    elif results[1]["status"] != "PASS":
        sys.exit(2)  # Data plane failure
    else:
        sys.exit(3)  # Decision plane failure


def print_summary(results):
    """Print human-readable and machine-readable summary."""
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print()
    
    for r in results:
        status_icon = "✅" if r["status"] == "PASS" else "❌" if r["status"] == "FAIL" else "⚠️"
        print(f"{status_icon} [{r['layer'].upper()}] {r['status']} ({r['case']})")
        print(f"   {r['details']}")
        print()
    
    # Machine-readable JSON summary
    summary = {
        r["layer"]: {
            "status": r["status"],
            "case": r["case"],
            "details": r["details"]
        }
        for r in results
    }
    
    print("JSON_SUMMARY_START")
    print(json.dumps(summary, indent=2))
    print("JSON_SUMMARY_END")
    print()


if __name__ == "__main__":
    main()
