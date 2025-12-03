#!/bin/bash
# FastAPI Lookup Endpoints Performance Testing Script
# Runs both sync and async lookup endpoint tests
# Reads FASTAPI_URL from config.py or environment variable

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Read FASTAPI_URL from config.py, fallback to environment variable or default
# Priority: 1. Environment variable 2. config.py 3. Default
if [ -z "$FASTAPI_URL" ]; then
    FASTAPI_URL=$(cd "$PROJECT_ROOT" && python3 -c "from config import FASTAPI_URL; print(FASTAPI_URL)" 2>/dev/null || echo "https://weaviate-pt-test.shorthills.ai")
fi

# Configuration
RF_VALUE=3
USER_COUNTS=(100)
LIMIT=200
SPAWN_RATE=10
RUN_TIME="5m"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║         FASTAPI LOOKUP ENDPOINTS PERFORMANCE TESTS                  ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Configuration:"
echo "  👥 Users: ${USER_COUNTS[*]}"
echo "  📊 Limit: $LIMIT"
echo "  🔄 RF: $RF_VALUE"
echo "  🚀 Spawn Rate: $SPAWN_RATE users/second"
echo "  ⏱️  Duration: $RUN_TIME per test"
echo "  🌐 FastAPI URL: $FASTAPI_URL"
echo ""
echo "This script will run:"
echo "  - GraphQL Lookup Sync (Hybrid): ${#USER_COUNTS[@]} user counts × 1 test = ${#USER_COUNTS[@]} tests"
echo "  - GraphQL Lookup Async (Hybrid): ${#USER_COUNTS[@]} user counts × 1 test = ${#USER_COUNTS[@]} tests"
echo "  Total: $(( ${#USER_COUNTS[@]} * 2 )) tests"
echo ""

# Check if we're in the right directory
if [ ! -f "locustfile_graphql_lookup_sync.py" ] || [ ! -f "locustfile_graphql_lookup_async.py" ]; then
    echo "${RED}❌ Error: Locust files not found!${NC}"
    echo "   Please run this script from: performance_testing/multi_collection/"
    exit 1
fi

# Check if query files exist
echo "═══════════════════════════════════════════════════════════════════════"
echo "Checking Query Files"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""

MISSING_QUERIES=false

if [ ! -f "queries/queries_hybrid_09_${LIMIT}.json" ]; then
    echo "${YELLOW}⚠️  Missing: queries/queries_hybrid_09_${LIMIT}.json${NC}"
    MISSING_QUERIES=true
fi

if [ "$MISSING_QUERIES" = true ]; then
    echo ""
    echo "${YELLOW}⚠️  Some query files are missing.${NC}"
    echo "   The tests will still run, but make sure query files exist."
    echo "   You can generate them with:"
    echo "   python3 ../../utilities/generate_all_queries.py --type multi --search-types hybrid_09 --limits $LIMIT"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "${GREEN}✅ All query files found${NC}"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "Starting Performance Tests"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""

# Function to run a single test
run_test() {
    local locustfile=$1
    local test_name=$2
    local user_count=$3
    local test_num=$4
    local total_tests=$5
    
    echo ""
    echo "${BLUE}╔══════════════════════════════════════════════════════════════════════╗${NC}"
    echo "${BLUE}║  Test $test_num/$total_tests: $test_name (Users: $user_count, Limit: $LIMIT, RF: $RF_VALUE)${NC}"
    echo "${BLUE}╚══════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    # Create report directory with simplified naming: lookup_RF{rf}_U{users}_L{limit}
    REPORT_DIR="../reports/multi_collection/lookup_RF${RF_VALUE}_U${user_count}_L${LIMIT}"
    mkdir -p "$REPORT_DIR"
    
    # Run Locust test
    echo "🚀 Running Locust test..."
    echo "   File: $locustfile"
    echo "   Test: $test_name"
    echo "   Users: $user_count"
    echo "   RF: $RF_VALUE"
    echo "   Limit: $LIMIT"
    echo "   Spawn Rate: $SPAWN_RATE"
    echo "   Duration: $RUN_TIME"
    echo "   FastAPI URL: $FASTAPI_URL"
    echo ""
    
    FASTAPI_URL="$FASTAPI_URL" locust -f "$locustfile" \
        --users "$user_count" \
        --spawn-rate "$SPAWN_RATE" \
        --run-time "$RUN_TIME" \
        --headless \
        --html "$REPORT_DIR/${test_name}_report.html" \
        --csv "$REPORT_DIR/${test_name}"
    
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -eq 0 ]; then
        echo ""
        echo "${GREEN}✅ Test complete: $test_name (Users: $user_count)${NC}"
        echo "   📊 Report: $REPORT_DIR/${test_name}_report.html"
        echo "   📈 CSV: $REPORT_DIR/${test_name}_stats.csv"
    else
        echo ""
        echo "${RED}❌ Test failed: $test_name (Users: $user_count) - Exit code: $EXIT_CODE${NC}"
    fi
    
    # Small delay between tests
    sleep 2
}

# Calculate total tests
TOTAL_TESTS=$(( ${#USER_COUNTS[@]} * 2 ))  # 2 test types × user counts
test_counter=0

# Run Sync Lookup tests (Hybrid) for each user count
echo ""
echo "${BLUE}═══════════════════════════════════════════════════════════════════════${NC}"
echo "${BLUE}GRAPHQL LOOKUP SYNC TESTS (HYBRID)${NC}"
echo "${BLUE}═══════════════════════════════════════════════════════════════════════${NC}"

for USER_COUNT in "${USER_COUNTS[@]}"; do
    ((test_counter++))
    run_test "locustfile_graphql_lookup_sync.py" "graphql_lookup_sync" "$USER_COUNT" "$test_counter" "$TOTAL_TESTS"
done

# Run Async Lookup tests (Hybrid) for each user count
echo ""
echo "${BLUE}═══════════════════════════════════════════════════════════════════════${NC}"
echo "${BLUE}GRAPHQL LOOKUP ASYNC TESTS (HYBRID)${NC}"
echo "${BLUE}═══════════════════════════════════════════════════════════════════════${NC}"

for USER_COUNT in "${USER_COUNTS[@]}"; do
    ((test_counter++))
    run_test "locustfile_graphql_lookup_async.py" "graphql_lookup_async" "$USER_COUNT" "$test_counter" "$TOTAL_TESTS"
done

# Generate combined report
echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "Generating Combined FastAPI Lookup Report"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""

cd ../report_generators
export PT_RF_VALUE=$RF_VALUE
export PT_LIMIT=$LIMIT
export PT_USER_COUNTS="${USER_COUNTS[*]}"  # Pass user counts as space-separated string
python3 generate_fastapi_lookup_report.py
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Combined FastAPI lookup report generated"
else
    echo ""
    echo "⚠️  Report generation had warnings (check above)"
fi
cd ../multi_collection

# Summary
echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                        ALL TESTS COMPLETE                            ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 Reports saved to: reports/multi_collection/lookup_RF${RF_VALUE}_U*/"
echo ""
echo "Summary:"
echo "  ✅ GraphQL Lookup Sync (Hybrid): ${#USER_COUNTS[@]} tests (${USER_COUNTS[*]} users)"
echo "  ✅ GraphQL Lookup Async (Hybrid): ${#USER_COUNTS[@]} tests (${USER_COUNTS[*]} users)"
echo "  🔄 RF Value: $RF_VALUE"
echo "  📈 Total: $TOTAL_TESTS tests completed"
echo ""
echo "Report locations:"
for USER_COUNT in "${USER_COUNTS[@]}"; do
    REPORT_DIR="../reports/multi_collection/lookup_RF${RF_VALUE}_U${USER_COUNT}_L${LIMIT}"
    echo "  👥 $USER_COUNT users (RF=$RF_VALUE):"
    echo "     - Sync Lookup: $REPORT_DIR/graphql_lookup_sync_report.html"
    echo "     - Async Lookup: $REPORT_DIR/graphql_lookup_async_report.html"
done
echo ""
echo "📊 Combined Report:"
# Build user counts string for simplified filename: lookup_combined_RF{rf}_U{users}_L{limit}.html
if [ ${#USER_COUNTS[@]} -eq 1 ]; then
    USERS_STR="U${USER_COUNTS[0]}"
else
    USERS_STR="U$(IFS=-; echo "${USER_COUNTS[*]}")"
fi
COMBINED_REPORT="../reports/multi_collection/lookup_combined_RF${RF_VALUE}_${USERS_STR}_L${LIMIT}.html"
echo "   $COMBINED_REPORT"
echo ""
echo "To view reports:"
for USER_COUNT in "${USER_COUNTS[@]}"; do
    REPORT_DIR="../reports/multi_collection/lookup_RF${RF_VALUE}_U${USER_COUNT}_L${LIMIT}"
    echo "  open $REPORT_DIR/graphql_lookup_sync_report.html"
    echo "  open $REPORT_DIR/graphql_lookup_async_report.html"
done
echo "  open $COMBINED_REPORT"
echo ""

