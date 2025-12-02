#!/bin/bash
# Export timelines helper script

echo "============================================================"
echo "EXPORTING HEDGE TIMELINES"
echo "============================================================"
echo ""

# Check if server is running
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "❌ Error: Server not running"
    echo "   Start server first: GAMMA_ONLY_TEST_MODE=true ./START_VALIDATION.sh"
    exit 1
fi

echo "✅ Server is running"
echo ""
echo "Exporting timelines..."
echo ""

# Export timelines
RESPONSE=$(curl -s -X POST http://localhost:8000/options/export-timelines)

# Parse response
RUN_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('run_id', 'unknown'))" 2>/dev/null || echo "unknown")
EXPORTED_COUNT=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('exported_count', 0))" 2>/dev/null || echo "0")
OUTPUT_DIR=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('output_dir', 'unknown'))" 2>/dev/null || echo "unknown")

echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

if [ "$EXPORTED_COUNT" -eq "0" ]; then
    echo "⚠️  No timelines exported (exported_count: 0)"
    echo "   This means no Gamma Scalper packages have completed yet"
    echo "   Let the simulation run longer and try again"
else
    echo "✅ Exported $EXPORTED_COUNT timeline(s)"
    echo "   Run ID: $RUN_ID"
    echo "   Output: $OUTPUT_DIR"
    echo ""
    echo "Files created:"
    ls -lh "$OUTPUT_DIR" 2>/dev/null || echo "   (check: $OUTPUT_DIR)"
    echo ""
    echo "To view a timeline:"
    echo "   cat $OUTPUT_DIR/*_timeline.txt | head -30"
fi

echo ""
echo "============================================================"

