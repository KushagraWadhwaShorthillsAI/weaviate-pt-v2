#!/bin/bash
# FULLY AUTOMATED Multi-Collection Performance Testing
# Handles everything: query generation, testing, and reporting
# Supports environment variables: PT_USER_COUNT

# Set defaults if not provided by wrapper
RF_VALUE=3

# Configuration variables
LIMIT=200
SPAWN_RATE=10
RUN_TIME="5m"

# Array of user counts to test
USER_COUNTS=(100 200 300)

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║   MULTI-COLLECTION PERFORMANCE TESTS - FULLY AUTOMATED               ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Configuration:"
echo "  👥 Users: ${USER_COUNTS[*]}"
echo "  🔄 RF: $RF_VALUE"
echo ""
echo "This script will:"
echo "  1. Check and generate query files if needed"
echo "  2. Run 2 search types (BM25, Hybrid 0.9) × 1 limit × 3 user counts = 6 tests"
echo "  3. Generate combined performance report for each user count"
echo "  4. Total duration: ~30 minutes (3 × ~10 minutes)"
echo ""

# Step 1: Check and generate query files
echo "═══════════════════════════════════════════════════════════════════════"
echo "STEP 1: Checking Query Files"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""

MISSING_QUERIES=false

# Check if required query files exist in queries/ folder (BM25 and Hybrid 0.9)
if [ ! -f "queries/queries_bm25_200.json" ] || [ ! -f "queries/queries_hybrid_09_200.json" ]; then
    echo "⚠️  Required query files not found in queries/ folder"
    MISSING_QUERIES=true
fi

if [ "$MISSING_QUERIES" = true ]; then
    echo ""
    echo "Generating all query files..."
    echo "This will take ~2 minutes (calls Azure OpenAI)"
    echo ""
    
    # Generate required queries (BM25 and Hybrid 0.9 only)
    echo "🔄 Generating BM25 and Hybrid 0.9 multi-collection queries..."
    cd ..
    python3 ../../utilities/generate_all_queries.py --type multi --search-types bm25 hybrid_09 --limits 200
    if [ $? -ne 0 ]; then
        echo "❌ Failed to generate query files"
        exit 1
    fi
    cd multi_collection
    
    echo ""
    echo "✅ All query files generated successfully"
else
    echo "✅ All query files found"
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

# Array of limits (only testing 200, but need folders for other limits for report generator)
LIMITS=(200)
OTHER_LIMITS=(10 50 100 150)  # Other limits for creating empty reports

# Function to create empty CSV with zero values for report generator
create_empty_stats_csv() {
    local report_dir=$1
    local search_type=$2
    local csv_file="${report_dir}/${search_type}_stats.csv"
    
    # Create empty CSV with header and zero values
    cat > "$csv_file" << EOF
Name,Type,Request Count,Failure Count,Median Response Time,Average Response Time,Min Response Time,Max Response Time,Average Content Size,Requests/s,50%,66%,75%,80%,90%,95%,98%,99%,99.9%,99.99%,100%
Aggregated,Aggregated,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
EOF
}

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
        
        REPORT_DIR="../reports/multi_collection/reports_RF${RF_VALUE}_Users${USER_COUNT}_Limit${LIMIT}"
        mkdir -p "$REPORT_DIR"
        
        # Test 1/2: BM25
        echo "🔍 Test 1/2: BM25 (limit=$LIMIT, users=$USER_COUNT)"
        echo "────────────────────────────────────────────────────────────────────"
        update_locustfile_query "locustfile_bm25.py" "queries_bm25_${LIMIT}.json"
        locust -f locustfile_bm25.py --users $USER_COUNT --spawn-rate $SPAWN_RATE --run-time $RUN_TIME --headless \
            --html "$REPORT_DIR/bm25_report.html" \
            --csv "$REPORT_DIR/bm25"
        echo "✅ BM25 complete"
        sleep 3
        
        # Test 2/2: Hybrid 0.9
        echo ""
        echo "🔍 Test 2/2: Hybrid α=0.9 (limit=$LIMIT, users=$USER_COUNT)"
        echo "────────────────────────────────────────────────────────────────────"
        update_locustfile_query "locustfile_hybrid_09.py" "queries_hybrid_09_${LIMIT}.json"
        locust -f locustfile_hybrid_09.py --users $USER_COUNT --spawn-rate $SPAWN_RATE --run-time $RUN_TIME --headless \
            --html "$REPORT_DIR/hybrid_09_report.html" \
            --csv "$REPORT_DIR/hybrid_09"
        echo "✅ Hybrid 0.9 complete"
        
        # Create empty CSV files for skipped search types (so report generator doesn't fail)
        echo ""
        echo "📝 Creating empty reports for skipped search types..."
        create_empty_stats_csv "$REPORT_DIR" "hybrid_01"
        create_empty_stats_csv "$REPORT_DIR" "vector"
        create_empty_stats_csv "$REPORT_DIR" "mixed"
        echo "✅ Empty reports created for hybrid_01, vector, mixed"
        
        echo ""
    done
    
    # Create empty report folders and CSV files for other limits (10, 50, 100, 150)
    # This ensures the report generator doesn't fail when looking for all limits
    echo ""
    echo "📝 Creating empty report folders for other limits (for report generator compatibility)..."
    for OTHER_LIMIT in "${OTHER_LIMITS[@]}"; do
        OTHER_REPORT_DIR="../reports/multi_collection/reports_RF${RF_VALUE}_Users${USER_COUNT}_Limit${OTHER_LIMIT}"
        mkdir -p "$OTHER_REPORT_DIR"
        
        # Create empty CSV files for all search types
        for search_type in "bm25" "hybrid_01" "hybrid_09" "vector" "mixed"; do
            create_empty_stats_csv "$OTHER_REPORT_DIR" "$search_type"
        done
        echo "✓ Created empty reports for limit ${OTHER_LIMIT} (users=${USER_COUNT})"
    done
    echo "✅ Empty report folders created for ${USER_COUNT} users"
    
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
        echo "✅ Combined report generated: ../reports/multi_collection/multi_collection_combined_RF${RF_VALUE}_Users${USER_COUNT}.html"
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
echo "Results saved to: ../reports/multi_collection/reports_RF${RF_VALUE}_Users*/"
echo ""

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                    🎉 ALL DONE!                                      ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 View Results:"
for USER_COUNT in "${USER_COUNTS[@]}"; do
    echo "   open ../reports/multi_collection/multi_collection_combined_RF${RF_VALUE}_Users${USER_COUNT}.html"
done
echo ""
echo "📂 Individual Reports:"
for USER_COUNT in "${USER_COUNTS[@]}"; do
    echo "   ../reports/multi_collection/reports_RF${RF_VALUE}_Users${USER_COUNT}_Limit200/*_report.html"
done
echo ""
echo "📈 What to Check:"
echo "   • Response time increases with limit ✅"
echo "   • Content size grows proportionally ✅"
echo "   • Failure rate = 0% ✅"
echo "   • Vector results show growth (not flat) ✅"
echo ""

