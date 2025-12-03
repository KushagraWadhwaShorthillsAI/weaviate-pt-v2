#!/bin/bash
# QUICK TEST - Complete PT workflow with minimal load
# 1. Generates all queries (uses cached embeddings)
# 2. Runs ALL tests: 5 types × 5 limits × 2 scenarios = 50 tests
# 3. Generates reports
# Users: 2, Duration: 20 seconds per test
# Total time: ~20 minutes

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║       QUICK PT TEST - ALL TYPES × ALL LIMITS (2 users, 20s)         ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "This will test:"
echo "  • Multi-Collection: 5 types × 5 limits = 25 tests"
echo "  • Single-Collection: 5 types × 5 limits = 25 tests"
echo "  • Total: 50 tests × 20 seconds = ~16-20 minutes"
echo ""
echo "Purpose: Comprehensive quick verification"
echo ""

read -p "Continue? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "❌ Cancelled"
    exit 0
fi

# Change to performance_testing directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../performance_testing" || exit 1

# Configuration
USERS=2
DURATION="20s"
SPAWN_RATE=1

# Test all limits
LIMITS=(10 50 100 150 200)

echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "STEP 1: Generate Query Files (if needed)"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""

# Generate ALL query files for ALL limits
echo "Generating all query files (5 types × 5 limits = 25 files per scenario)..."
echo "This uses cached embeddings (fast!)"
echo ""

python3 ../utilities/generate_all_queries.py --type multi
if [ $? -ne 0 ]; then
    echo "❌ Failed to generate multi-collection queries"
    exit 1
fi

python3 ../utilities/generate_all_queries.py --type single
if [ $? -ne 0 ]; then
    echo "❌ Failed to generate single-collection queries"
    exit 1
fi

echo "✅ All query files generated"

echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "STEP 2: Test Multi-Collection (5 types × 5 limits = 25 tests)"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""

cd multi_collection

test_count=0
total_tests=25

# Helper function to update and run test
run_test() {
    local locustfile=$1
    local search_type=$2
    local limit=$3
    
    ((test_count++))
    echo "🔍 Test $test_count/$total_tests: $search_type (limit=$limit)"
    
    # Update locustfile for this limit
    python3 << PYEOF
import re
with open('$locustfile', 'r') as f:
    content = f.read()
content = re.sub(r'queries/queries_${search_type}_\d+\.json', 'queries/queries_${search_type}_${limit}.json', content)
with open('$locustfile', 'w') as f:
    f.write(content)
PYEOF
    
    # Verify correct file is set
    expected_file="queries/queries_${search_type}_${limit}.json"
    actual_file=$(grep "queries_${search_type}" $locustfile | grep "with open\|filename =" | head -1 | grep -o "queries_${search_type}_[0-9]*\.json")
    
    if [ "$actual_file" = "queries_${search_type}_${limit}.json" ]; then
        echo "   ✅ Verified: Using $actual_file"
    else
        echo "   ⚠️  Warning: Expected queries_${search_type}_${limit}.json, got $actual_file"
    fi
    
    # Create results folder
    results_dir="../reports/multi_collection/reports_${limit}"
    mkdir -p "$results_dir"
    
    # Run test and save results
    locust -f $locustfile --users $USERS --spawn-rate $SPAWN_RATE --run-time $DURATION --headless \
        --html "$results_dir/${search_type}_report.html" \
        --csv "$results_dir/${search_type}" 2>&1 | grep -A 2 "Aggregated" | tail -3
    
    echo "   💾 Saved to: reports/multi_collection/reports_${limit}/${search_type}_*"
    echo ""
}

# Test each search type for each limit
for LIMIT in "${LIMITS[@]}"; do
    run_test "locustfile_bm25.py" "bm25" $LIMIT
    run_test "locustfile_hybrid_01.py" "hybrid_01" $LIMIT
    run_test "locustfile_hybrid_09.py" "hybrid_09" $LIMIT
    run_test "locustfile_vector.py" "vector" $LIMIT
    run_test "locustfile_mixed.py" "mixed" $LIMIT
done

cd ..

echo "═══════════════════════════════════════════════════════════════════════"
echo "STEP 3: Test Single-Collection (5 types × 5 limits = 25 tests)"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""

cd single_collection

test_count=0
total_tests=25

# Redefine run_test for single-collection (different results path)
run_test_single() {
    local locustfile=$1
    local search_type=$2
    local limit=$3
    
    ((test_count++))
    echo "🔍 Test $test_count/$total_tests: $search_type (limit=$limit) [Single]"
    
    # Update locustfile for this limit
    python3 << PYEOF
import re
with open('$locustfile', 'r') as f:
    content = f.read()
content = re.sub(r'queries/queries_${search_type}_\d+\.json', 'queries/queries_${search_type}_${limit}.json', content)
with open('$locustfile', 'w') as f:
    f.write(content)
PYEOF
    
    # Verify correct file is set
    actual_file=$(grep "queries_${search_type}" $locustfile | grep "with open\|filename =" | head -1 | grep -o "queries_${search_type}_[0-9]*\.json")
    
    if [ "$actual_file" = "queries_${search_type}_${limit}.json" ]; then
        echo "   ✅ Verified: Using $actual_file"
    else
        echo "   ⚠️  Warning: Expected queries_${search_type}_${limit}.json, got $actual_file"
    fi
    
    # Create results folder
    results_dir="../reports/single_collection/reports_${limit}"
    mkdir -p "$results_dir"
    
    # Run test and save results
    locust -f $locustfile --users $USERS --spawn-rate $SPAWN_RATE --run-time $DURATION --headless \
        --html "$results_dir/${search_type}_report.html" \
        --csv "$results_dir/${search_type}" 2>&1 | grep -A 2 "Aggregated" | tail -3
    
    echo "   💾 Saved to: reports/single_collection/reports_${limit}/${search_type}_*"
    echo ""
}

# Test each search type for each limit
for LIMIT in "${LIMITS[@]}"; do
    run_test_single "locustfile_bm25.py" "bm25" $LIMIT
    run_test_single "locustfile_hybrid_01.py" "hybrid_01" $LIMIT
    run_test_single "locustfile_hybrid_09.py" "hybrid_09" $LIMIT
    run_test_single "locustfile_single_vector.py" "vector" $LIMIT
    run_test_single "locustfile_mixed.py" "mixed" $LIMIT
done

cd ..

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                    ✅ ALL TESTS COMPLETE!                            ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 Test Summary:"
echo "   • Multi-Collection: 5 types × 5 limits = 25 tests"
echo "   • Single-Collection: 5 types × 5 limits = 25 tests"
echo "   • Total: 50 quick tests"
echo ""

echo "═══════════════════════════════════════════════════════════════════════"
echo "STEP 4: Generate Reports"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""

cd report_generators

echo "Generating multi-collection report..."
python3 generate_combined_report.py 2>&1 | grep -E "✅|Created|Found data"

echo ""
echo "Generating single-collection report..."
python3 generate_single_report.py 2>&1 | grep -E "✅|Created|Found data"

cd ../..

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                    🎉 COMPLETE - REPORTS GENERATED!                  ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 View Reports:"
echo "   open reports/multi_collection/multi_collection_combined_*.html"
echo "   open reports/single_collection/single_collection_report.html"
echo ""
echo "💡 This was a quick verification test (2 users, 20 seconds)."
echo "   All files verified loading correctly during tests."
echo ""
echo "   For full performance testing (100 users, 5 minutes), run:"
echo "   ./run_all_pt_tests.sh"
echo ""

