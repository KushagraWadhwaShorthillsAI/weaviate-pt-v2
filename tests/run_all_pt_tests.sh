#!/bin/bash
# MASTER SCRIPT - Runs ALL Performance Tests
# Handles query generation and all test scenarios

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║         WEAVIATE PERFORMANCE TESTING - MASTER SCRIPT                 ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "This script will:"
echo "  1. Generate ALL query files (if needed)"
echo "  2. Run Multi-Collection tests (25 tests)"
echo "  3. Run Single-Collection tests (25 tests)"
echo "  4. Generate all reports"
echo ""
echo "Total time: ~4.5 hours"
echo ""

read -p "Run ALL tests? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "❌ Cancelled"
    exit 0
fi

# Change to performance_testing directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../performance_testing" || exit 1

echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "STEP 1: Generate Query Files"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""

# Generate multi-collection queries
echo "🔄 Generating multi-collection queries..."
python ../utilities/generate_all_queries.py --type multi
if [ $? -ne 0 ]; then
    echo "❌ Failed to generate multi-collection queries"
    exit 1
fi

# Generate single-collection queries
echo ""
echo "🔄 Generating single-collection queries..."
python ../utilities/generate_all_queries.py --type single
if [ $? -ne 0 ]; then
    echo "❌ Failed to generate single-collection queries"
    exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "STEP 2: Run Multi-Collection Tests (~2h 15m)"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""

cd multi_collection
./run_multi_collection_all_limits.sh
cd ..

echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "STEP 3: Run Single-Collection Tests (~2h 15m)"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""

cd single_collection
python3 run_automated_tests.py
cd ..

echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "STEP 4: Generate All Reports"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""

cd report_generators
python3 generate_combined_report.py
python3 generate_single_report.py
cd ../..

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                    🎉 ALL TESTS COMPLETE!                            ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 View Reports:"
echo "   open reports/multi_collection/multi_collection_report*.html"
echo "   open reports/single_collection/single_collection_report.html"
echo ""
echo "📂 Detailed Results:"
echo "   reports/multi_collection/reports_*/"
echo "   reports/single_collection/reports_*/"
echo ""

