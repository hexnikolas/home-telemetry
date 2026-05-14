#!/bin/bash

# Test script to run pytest in all testable directories
# Usage: ./test.sh

set -e

TESTABLE_DIRS=(
    "services/api"
    "services/ingestion"
    "services/jobs"
    "services/notifier"
    "shared"
)

TOTAL_TESTS=0
FAILED_DIRS=()

echo "================================"
echo "Running test suite for all services"
echo "================================"
echo ""

for dir in "${TESTABLE_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        echo "⚠️  Skipping $dir (directory not found)"
        continue
    fi
    
    if [ ! -f "$dir/pyproject.toml" ]; then
        echo "⚠️  Skipping $dir (no pyproject.toml found)"
        continue
    fi
    
    echo "📦 Testing: $dir"
    echo "─────────────────────────────────"
    
    if cd "$dir" && poetry run pytest --tb=short -q; then
        echo "✅ $dir: PASSED"
    else
        echo "❌ $dir: FAILED"
        FAILED_DIRS+=("$dir")
    fi
    
    cd - > /dev/null
    echo ""
done

echo "================================"
echo "Test run complete"
echo "================================"

if [ ${#FAILED_DIRS[@]} -eq 0 ]; then
    echo "✅ All test suites passed!"
    exit 0
else
    echo "❌ Failed test suites:"
    for dir in "${FAILED_DIRS[@]}"; do
        echo "   - $dir"
    done
    exit 1
fi
