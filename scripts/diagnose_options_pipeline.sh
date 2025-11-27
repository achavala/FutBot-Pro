#!/usr/bin/env bash
# 3-Layer Diagnostic Plan for Options Trading Pipeline
# Thin wrapper around Python diagnostic script

set -euo pipefail

# Configuration
API_BASE="${API_BASE:-http://localhost:8000}"
PY_SCRIPT="scripts/diagnose_options_pipeline.py"
LOG_DIR="${LOG_DIR:-logs}"

echo "Running options pipeline diagnostic against ${API_BASE} ..."
echo

# Run Python diagnostic
python3 "${PY_SCRIPT}"
STATUS=$?

echo

if [ $STATUS -eq 0 ]; then
    echo "✅ Diagnostic PASSED - All layers working"
    exit 0
elif [ $STATUS -eq 1 ]; then
    echo "❌ Diagnostic FAILED - Execution plane issue (exit code ${STATUS})"
    echo
    echo "Recent logs:"
    echo "---------------------------------------------------"
    if [ -d "$LOG_DIR" ]; then
        tail -n 50 "$LOG_DIR"/*.log 2>/dev/null | grep -i "force_buy\|broker\|options" || echo "No relevant logs found"
    else
        echo "Log directory not found: $LOG_DIR"
    fi
    exit 1
elif [ $STATUS -eq 2 ]; then
    echo "❌ Diagnostic FAILED - Data plane issue (exit code ${STATUS})"
    echo
    echo "Recent logs:"
    echo "---------------------------------------------------"
    if [ -d "$LOG_DIR" ]; then
        tail -n 50 "$LOG_DIR"/*.log 2>/dev/null | grep -i "options.*chain\|quote\|greeks" || echo "No relevant logs found"
    else
        echo "Log directory not found: $LOG_DIR"
    fi
    exit 2
elif [ $STATUS -eq 3 ]; then
    echo "❌ Diagnostic FAILED - Decision plane issue (exit code ${STATUS})"
    echo
    echo "Recent logs:"
    echo "---------------------------------------------------"
    if [ -d "$LOG_DIR" ]; then
        tail -n 100 "$LOG_DIR"/*.log 2>/dev/null | grep -i "optionsagent\|candidates\|accept\|reject" || echo "No relevant logs found"
    else
        echo "Log directory not found: $LOG_DIR"
    fi
    echo
    echo "Monitor logs in real-time:"
    echo "  tail -f $LOG_DIR/*.log | grep -i 'optionsagent'"
    exit 3
else
    echo "❌ Diagnostic FAILED - Unknown error (exit code ${STATUS})"
    exit $STATUS
fi
