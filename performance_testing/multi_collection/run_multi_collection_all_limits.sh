#!/bin/bash
# FULLY AUTOMATED Multi-Collection Performance Testing
# Handles everything: query generation, testing, and reporting
# Supports environment variables: PT_USER_COUNT

# Set defaults if not provided by wrapper
RF_VALUE=3

# Configuration variables
LIMIT=200
RUN_TIME="30m"

# Array of user counts to test
USER_COUNTS=(200 300 400)

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║   MULTI-COLLECTION PERFORMANCE TESTS - FULLY AUTOMATED               ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Configuration:"
echo "  👥 Users: ${USER_COUNTS[*]}"
echo "  🔄 RF: $RF_VALUE"
echo "  ⏱️  Duration: $RUN_TIME per test"
echo ""
echo "This script will:"
echo "  1. Check and generate query files if needed"
echo "  2. Run Hybrid 0.9 search type × 1 limit × 3 user counts = 3 tests"
echo "  3. Generate combined performance report for each user count"
echo "  4. Total duration: ~90 minutes (3 × ~30 minutes)"
echo ""

# Step 1: Check and generate query files
echo "═══════════════════════════════════════════════════════════════════════"
echo "STEP 1: Checking Query Files"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""

MISSING_QUERIES=false

# Check if required query files exist in queries/ folder (Hybrid 0.9 only)
if [ ! -f "queries/queries_hybrid_09_200.json" ]; then
    echo "⚠️  Required query files not found in queries/ folder"
    MISSING_QUERIES=true
fi

if [ "$MISSING_QUERIES" = true ]; then
    echo ""
    echo "Generating query files..."
    echo "This will take ~1 minute (calls Azure OpenAI)"
    echo ""
    
    # Generate required queries (Hybrid 0.9 only)
    echo "🔄 Generating Hybrid 0.9 multi-collection queries..."
    cd ..
    python3 ../../utilities/generate_all_queries.py --type multi --search-types hybrid_09 --limits 200
    if [ $? -ne 0 ]; then
        echo "❌ Failed to generate query files"
        exit 1
    fi
    cd multi_collection
    
    echo ""
    echo "✅ Query files generated successfully"
else
    echo "✅ Query files found"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "STEP 2: Running Performance Tests"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""

# Function to update locustfile with correct query filename
update_locustfile_query() {
    local locustfile=$1
    local new_filename=$2
    
    python3 << PYEOF
import re
with open('$locustfile', 'r') as f:
    content = f.read()

# Replace the query filename
content = re.sub(
    r'(with\s+open\s*\(\s*["\'])queries_[^"\']+\.json',
    r'\1$new_filename',
    content
)

with open('$locustfile', 'w') as f:
    f.write(content)
PYEOF
}

# Update vector locustfile limit
update_vector_limit() {
    local limit=$1
    python3 << PYEOF
import re
with open('locustfile_vector.py', 'r') as f:
    content = f.read()
content = re.sub(r'limit\s*=\s*\d+', f'limit = $limit', content)
with open('locustfile_vector.py', 'w') as f:
    f.write(content)
PYEOF
}

# Array of limits (only testing 200)
LIMITS=(200)

# Run tests for each user count
for USER_COUNT in "${USER_COUNTS[@]}"; do
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════════╗"
    echo "║                  TESTING WITH $USER_COUNT USERS                         ║"
    echo "╚══════════════════════════════════════════════════════════════════════╝"
    echo ""
    
    # Run tests for each limit
    for LIMIT in "${LIMITS[@]}"; do
        echo "╔══════════════════════════════════════════════════════════════════════╗"
        echo "║                      TESTING LIMIT $LIMIT                                ║"
        echo "╚══════════════════════════════════════════════════════════════════════╝"
        echo ""
        
        REPORT_DIR="../reports/multi_collection/reports_RF${RF_VALUE}_U${USER_COUNT}_L${LIMIT}"
        mkdir -p "$REPORT_DIR"
        
        # Calculate spawn rate dynamically: ramp up over ~6 seconds
        SPAWN_RATE=$((USER_COUNT / 6))
        if [ $SPAWN_RATE -lt 10 ]; then
            SPAWN_RATE=10  # Minimum spawn rate
        fi
        
        # Test: Hybrid 0.9
        echo "🔍 Test: Hybrid α=0.9 (limit=$LIMIT, users=$USER_COUNT, spawn-rate=$SPAWN_RATE)"
        echo "────────────────────────────────────────────────────────────────────"
        update_locustfile_query "locustfile_hybrid_09.py" "queries_hybrid_09_${LIMIT}.json"
        locust -f locustfile_hybrid_09.py --users $USER_COUNT --spawn-rate $SPAWN_RATE --run-time $RUN_TIME --headless \
            --html "$REPORT_DIR/hybrid_09_report.html" \
            --csv "$REPORT_DIR/hybrid_09"
        echo "✅ Hybrid 0.9 complete"
        
        # Commented out: BM25 test
        # echo ""
        # echo "🔍 Test 1/2: BM25 (limit=$LIMIT, users=$USER_COUNT)"
        # echo "────────────────────────────────────────────────────────────────────"
        # update_locustfile_query "locustfile_bm25.py" "queries_bm25_${LIMIT}.json"
        # locust -f locustfile_bm25.py --users $USER_COUNT --spawn-rate $SPAWN_RATE --run-time $RUN_TIME --headless \
        #     --html "$REPORT_DIR/bm25_report.html" \
        #     --csv "$REPORT_DIR/bm25"
        # echo "✅ BM25 complete"
        # sleep 3
        
        echo ""
    done
    
    # Generate combined report for this user count
    echo ""
    echo "═══════════════════════════════════════════════════════════════════════"
    echo "Generating Combined Report for ${USER_COUNT} users"
    echo "═══════════════════════════════════════════════════════════════════════"
    echo ""
    
    cd ../report_generators
    # Pass RF and Users info to report generator via environment variables
    export PT_RF_VALUE=$RF_VALUE
    export PT_USER_COUNT=$USER_COUNT
    python3 generate_combined_report.py
    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ Combined report generated: ../reports/multi_collection/multi_collection_combined_RF${RF_VALUE}_U${USER_COUNT}.html"
    else
        echo ""
        echo "⚠️  Report generation had warnings (check above)"
    fi
    cd ../multi_collection
    
    if [ "$USER_COUNT" != "${USER_COUNTS[-1]}" ]; then
        echo ""
        echo "⏸️  ${USER_COUNT} users complete. Waiting 15 seconds before next user count..."
        sleep 15
    fi
done

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║              ✅ ALL MULTI-COLLECTION TESTS COMPLETE!                 ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Results saved to: ../reports/multi_collection/reports_RF${RF_VALUE}_U*/"
echo ""

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                    🎉 ALL DONE!                                      ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 View Results:"
for USER_COUNT in "${USER_COUNTS[@]}"; do
    echo "   open ../reports/multi_collection/multi_collection_combined_RF${RF_VALUE}_U${USER_COUNT}.html"
done
echo ""
echo "📂 Individual Reports:"
for USER_COUNT in "${USER_COUNTS[@]}"; do
    echo "   ../reports/multi_collection/reports_RF${RF_VALUE}_U${USER_COUNT}_L200/*_report.html"
done
echo ""
echo "📈 What to Check:"
echo "   • Response time increases with limit ✅"
echo "   • Content size grows proportionally ✅"
echo "   • Failure rate = 0% ✅"
echo "   • Vector results show growth (not flat) ✅"
echo ""

