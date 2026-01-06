#!/bin/bash
# Generate Excel reports for all user counts
# This script scans all user count reports and creates a combined Excel file

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║              EXCEL REPORT GENERATOR - ALL USER COUNTS               ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

cd "$(dirname "$0")" || exit 1

# Activate virtual environment if it exists
if [ -f "../../ptVenv/bin/activate" ]; then
    source ../../ptVenv/bin/activate
    echo "✅ Activated virtual environment"
fi

# Get RF value (default to 3)
RF_VALUE=${PT_RF_VALUE:-3}

echo "Configuration:"
echo "  🔄 RF: $RF_VALUE"
echo ""

# Set environment variable for the script
export PT_RF_VALUE=$RF_VALUE

# Run the Excel report generator
echo "📊 Generating Excel report for all user counts..."
python3 generate_excel_report.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Excel report generated successfully!"
    echo ""
    echo "📂 Report location:"
    echo "   ../reports/multi_collection/multi_collection_performance_RF${RF_VALUE}.xlsx"
else
    echo ""
    echo "❌ Failed to generate Excel report"
    exit 1
fi

