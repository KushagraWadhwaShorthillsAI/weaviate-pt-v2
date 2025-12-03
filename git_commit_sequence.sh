#!/bin/bash
# Git Commit Sequence - Add all new/modified files (excluding reports and ignored files)
# This script stages files that should be committed to git

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║              GIT COMMIT SEQUENCE - STAGING FILES                    ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# Check git status first
echo "📋 Current git status:"
echo "────────────────────────────────────────────────────────────────────"
git status --short
echo ""

# Stage modified .gitignore
echo "📝 Staging .gitignore..."
git add .gitignore

# Stage report generator (with user count fix) - if modified
if git diff --quiet performance_testing/report_generators/generate_combined_report.py; then
    echo "ℹ️  Report generator already committed (no changes)"
else
    echo "📝 Staging report generator fixes..."
    git add performance_testing/report_generators/generate_combined_report.py
fi

# Stage new API test files
echo "📝 Staging API test files..."
git add performance_testing/api/tests/

# Stage documentation files
echo "📝 Staging documentation files..."
git add performance_testing/docs/

# Stage new locustfiles
echo "📝 Staging new locustfiles..."
git add performance_testing/single_collection/locustfile_async_vector.py
git add performance_testing/single_collection/locustfile_single_vector.py

# Stage this script itself
echo "📝 Staging git commit sequence script..."
git add git_commit_sequence.sh

echo ""
echo "✅ Files staged successfully!"
echo ""
echo "📋 Staged files:"
echo "────────────────────────────────────────────────────────────────────"
git status --short
echo ""
echo "⚠️  Note: Reports directory is excluded (in .gitignore)"
echo ""
echo "To commit these changes:"
echo "  git commit -m 'Add new test files, documentation, and fix user count in reports'"
echo ""

