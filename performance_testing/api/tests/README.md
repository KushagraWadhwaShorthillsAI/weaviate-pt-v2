# FastAPI Async Functionality Tests

This directory contains test scripts to validate the async functionality of the FastAPI Weaviate API.

## Test Scripts

### 1. `test_async_fanout.py`
Validates that async task fanout is working correctly:
- Tests BM25 async endpoint
- Tests Hybrid async endpoint
- Validates parallel execution timing
- Checks task creation and execution

**Run:**
```bash
cd performance_testing/api/tests
python test_async_fanout.py
```

### 2. `test_request_response_logging.py`
Validates request/response logging:
- Tests request logging
- Tests multiple request tracking
- Tests error handling logging

**Run:**
```bash
cd performance_testing/api/tests
python test_request_response_logging.py
```

### 3. `run_all_tests.py`
Runs all test suites in sequence.

**Run:**
```bash
cd performance_testing/api/tests
python run_all_tests.py
```

## Prerequisites

1. **FastAPI server must be running:**
   ```bash
   cd performance_testing/api
   uvicorn fastapi_weaviate:app --host 0.0.0.0 --port 8000
   ```

2. **Environment variables (optional):**
   ```bash
   export FASTAPI_URL=http://localhost:8000  # Default
   ```

## What the Tests Validate

### Async Task Fanout
- ✅ Tasks are created for each collection (9 total)
- ✅ Tasks execute in parallel (not sequentially)
- ✅ Total execution time ≈ slowest task (not sum of all tasks)
- ✅ All results are collected correctly
- ✅ Both BM25 and Hybrid search modes work

### Request/Response Logging
- ✅ Requests are logged with unique request IDs
- ✅ Task creation and execution is logged
- ✅ Response timing is tracked
- ✅ Errors are properly logged
- ✅ Multiple concurrent requests are tracked separately

## Expected Output

When tests pass, you should see:
- ✓ All checks passed
- Timing information showing parallel execution
- Detailed results for each collection
- Validation summaries

## Log Files

Check `fastapi_weaviate.log` in the `performance_testing/api/` directory for detailed logs:
- Request IDs
- Task creation timestamps
- Task execution times
- Error details
- Response summaries

## Troubleshooting

### Tests fail with connection errors
- Make sure FastAPI server is running
- Check `FASTAPI_URL` environment variable
- Verify network connectivity

### Tests show sequential execution
- Check server logs for task creation
- Verify `asyncio.create_task()` is being used
- Check for blocking operations in task functions

### No results returned
- Verify Weaviate is accessible
- Check collections exist
- Review error logs in `fastapi_weaviate.log`

