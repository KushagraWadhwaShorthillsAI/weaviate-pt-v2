#!/bin/bash
################################################################################
# Quick Test - Validates parallel testing setup without running full tests
################################################################################

set -e

echo "================================================================================"
echo "🔍 PARALLEL TESTING - Quick Validation"
echo "================================================================================"
echo ""

cd "$(dirname "$0")"

echo "1️⃣ Checking query files..."
EXPECTED_FILES=25
ACTUAL_FILES=$(ls queries/*.json 2>/dev/null | wc -l)

if [ "$ACTUAL_FILES" -eq "$EXPECTED_FILES" ]; then
    echo "   ✅ Found all $ACTUAL_FILES query files"
else
    echo "   ❌ Expected $EXPECTED_FILES files, found $ACTUAL_FILES"
    echo "   Run: python generate_parallel_queries.py --search-types all"
    exit 1
fi

echo ""
echo "2️⃣ Checking locustfiles..."
for file in locustfile_*.py; do
    if [ -f "$file" ]; then
        echo "   ✅ $file exists"
    else
        echo "   ❌ Missing $file"
        exit 1
    fi
done

echo ""
echo "3️⃣ Validating query structure (sample: queries_vector_200.json)..."
python3 << 'EOF'
import json
import sys

try:
    with open('queries/queries_vector_200.json', 'r') as f:
        queries = json.load(f)
    
    # Validate structure
    assert len(queries) == 40, f"Expected 40 query sets, got {len(queries)}"
    
    first_set = queries[0]
    assert "query_text" in first_set, "Missing query_text field"
    assert "queries" in first_set, "Missing queries field"
    assert len(first_set["queries"]) == 9, f"Expected 9 queries per set, got {len(first_set['queries'])}"
    
    first_query = first_set["queries"][0]
    assert "collection" in first_query, "Missing collection field"
    assert "graphql" in first_query, "Missing graphql field"
    assert "SongLyrics" in first_query["collection"], "Invalid collection name"
    
    print("   ✅ Query structure validated")
    print(f"   ✅ 40 query sets × 9 collections = {len(queries) * 9} individual queries")
    
except Exception as e:
    print(f"   ❌ Validation failed: {e}")
    sys.exit(1)
EOF

echo ""
echo "4️⃣ Testing Python imports..."
python3 << 'EOF'
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

try:
    import config
    import gevent
    from locust import HttpUser, task, events
    print("   ✅ All required imports successful")
    print(f"   ✅ Weaviate URL: {config.WEAVIATE_URL}")
except ImportError as e:
    print(f"   ❌ Import failed: {e}")
    sys.exit(1)
EOF

echo ""
echo "5️⃣ Checking embeddings cache..."
if [ -f "../embeddings_cache.json" ]; then
    echo "   ✅ embeddings_cache.json exists"
    CACHE_SIZE=$(wc -c < "../embeddings_cache.json")
    echo "   ✅ Cache size: $CACHE_SIZE bytes"
else
    echo "   ⚠️  Warning: embeddings_cache.json not found in parent directory"
    echo "   This is OK if queries are already generated"
fi

echo ""
echo "================================================================================"
echo "✅ VALIDATION COMPLETE - All checks passed!"
echo "================================================================================"
echo ""
echo "🎯 Ready to run tests:"
echo ""
echo "   Option 1: Run all tests"
echo "   $ ./run_parallel_tests.sh"
echo ""
echo "   Option 2: Run single test (quick 30s test)"
echo "   $ locust -f locustfile_vector.py --users 10 --spawn-rate 2 --run-time 30s --headless"
echo ""
echo "   Option 3: Interactive mode (web UI)"
echo "   $ locust -f locustfile_vector.py"
echo "   $ # Then open http://localhost:8089"
echo ""
echo "================================================================================"

