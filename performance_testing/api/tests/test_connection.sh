#!/bin/bash
# Quick test script to verify Locust can connect to FastAPI
# This runs a minimal Locust test with 1 user for 10 seconds
# Reads FASTAPI_URL from config.py or environment variable

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Read FASTAPI_URL from config.py, fallback to environment variable or default
# Priority: 1. Environment variable 2. config.py 3. Default
if [ -z "$FASTAPI_URL" ]; then
    FASTAPI_URL=$(cd "$PROJECT_ROOT" && python3 -c "from config import FASTAPI_URL; print(FASTAPI_URL)" 2>/dev/null || echo "http://localhost:8000")
fi

echo "=========================================="
echo "Testing Locust connection to FastAPI"
echo "=========================================="
echo ""
echo "FastAPI URL: $FASTAPI_URL"
echo ""

# Check if FastAPI is running
echo "Step 1: Checking if FastAPI is running..."
if curl -s -f "$FASTAPI_URL/health" > /dev/null 2>&1; then
    echo "✓ FastAPI is running"
else
    echo "✗ FastAPI is NOT running at $FASTAPI_URL"
    echo "  Please start FastAPI first:"
    echo "  cd performance_testing/api"
    echo "  uvicorn fastapi_weaviate:app --host 0.0.0.0 --port 8000"
    exit 1
fi
echo ""

# Test the test endpoint
echo "Step 2: Testing FastAPI /test endpoint..."
TEST_RESULT=$(curl -s "$FASTAPI_URL/test")
if echo "$TEST_RESULT" | grep -q '"fastapi_status"'; then
    echo "✓ Test endpoint is working"
    echo "$TEST_RESULT" | python3 -m json.tool 2>/dev/null | head -20
else
    echo "✗ Test endpoint failed"
fi
echo ""

# Run Locust test
echo "Step 3: Running Locust connection test..."
echo "  This will run 1 user for 10 seconds..."
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Run Locust test
locust -f test_locust_connection.py \
  --users 1 \
  --spawn-rate 1 \
  --run-time 10s \
  --headless \
  --host "$FASTAPI_URL" \
  --html /tmp/locust_connection_test.html \
  2>&1 | grep -v "KeyboardInterrupt\|Traceback\|File\|line\|Greenlet" || true

echo ""
echo "=========================================="
echo "Test complete!"
echo "=========================================="
echo "Check /tmp/locust_connection_test.html for detailed results"

