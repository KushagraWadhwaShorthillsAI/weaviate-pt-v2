#!/bin/bash
################################################################################
# PARALLEL COLLECTION TESTING - Automated Test Runner
# Runs all 5 search types with different limits to compare parallel execution
# vs. multi-collection single-query approach.
################################################################################

set -e  # Exit on error

echo "================================================================================"
echo "🚀 PARALLEL COLLECTION TESTING - Automated Test Suite"
echo "================================================================================"
echo ""
echo "This script tests parallel execution of 9 collection queries:"
echo "  • Vector Search (nearVector)"
echo "  • BM25 Search (keyword)"
echo "  • Hybrid Search Alpha=0.1 (90% vector + 10% BM25)"
echo "  • Hybrid Search Alpha=0.9 (10% vector + 90% BM25)"
echo "  • Mixed Search (rotating types)"
echo ""
echo "Each test sends 9 PARALLEL HTTP requests (one per collection) simultaneously."
echo "================================================================================"
echo ""

# Default test parameters
USERS=${USERS:-100}
SPAWN_RATE=${SPAWN_RATE:-5}
RUN_TIME=${RUN_TIME:-5m}
LIMIT=${LIMIT:-200}

echo "📋 Test Configuration:"
echo "   Users: $USERS"
echo "   Spawn Rate: $SPAWN_RATE users/sec"
echo "   Run Time: $RUN_TIME"
echo "   Result Limit: $LIMIT per collection"
echo ""
read -p "Press Enter to continue or Ctrl+C to abort..."
echo ""

# Navigate to parallel_testing directory
cd "$(dirname "$0")"

# Create results directory in reports/parallel_testing
REPORTS_BASE_DIR="$(dirname "$0")/../reports/parallel_testing"
RESULTS_DIR="$REPORTS_BASE_DIR/results_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"

echo "================================================================================"
echo "📁 Results will be saved to: $RESULTS_DIR/"
echo "================================================================================"
echo ""

# Function to run a test
run_test() {
    local TEST_NAME=$1
    local LOCUSTFILE=$2
    local OUTPUT_PREFIX="${RESULTS_DIR}/${TEST_NAME}_limit${LIMIT}"
    
    echo "--------------------------------------------------------------------------------"
    echo "🔥 Running: $TEST_NAME"
    echo "   Locustfile: $LOCUSTFILE"
    echo "   Output: ${OUTPUT_PREFIX}_*"
    echo "--------------------------------------------------------------------------------"
    
    locust -f "$LOCUSTFILE" \
        --users "$USERS" \
        --spawn-rate "$SPAWN_RATE" \
        --run-time "$RUN_TIME" \
        --headless \
        --html "${OUTPUT_PREFIX}_report.html" \
        --csv "${OUTPUT_PREFIX}" \
        --logfile "${OUTPUT_PREFIX}.log"
    
    echo "✅ Completed: $TEST_NAME"
    echo ""
}

# Run all tests
echo "================================================================================"
echo "🏁 Starting Test Execution..."
echo "================================================================================"
echo ""

run_test "1_Vector" "locustfile_vector.py"
run_test "2_BM25" "locustfile_bm25.py"
run_test "3_Hybrid_01" "locustfile_hybrid_01.py"
run_test "4_Hybrid_09" "locustfile_hybrid_09.py"
run_test "5_Mixed" "locustfile_mixed.py"

echo "================================================================================"
echo "✅ ALL TESTS COMPLETED!"
echo "================================================================================"
echo ""
echo "📊 Results Summary:"
echo "   Location: $RESULTS_DIR/"
echo ""
echo "   HTML Reports:"
ls -lh "$RESULTS_DIR"/*.html
echo ""
echo "   CSV Stats:"
ls -lh "$RESULTS_DIR"/*.csv
echo ""
echo "   Log Files:"
ls -lh "$RESULTS_DIR"/*.log
echo ""
echo "================================================================================"
echo "🎯 Next Steps:"
echo "   1. Open HTML reports in browser to view detailed metrics"
echo "   2. Compare with multi-collection results to see performance difference"
echo "   3. Analyze CSV files for statistical analysis"
echo "================================================================================"

