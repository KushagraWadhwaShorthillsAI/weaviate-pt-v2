# FastAPI Weaviate GraphQL API

FastAPI application that provides endpoints for querying Weaviate:
1. **`/graphql`** - Normal GraphQL endpoint (single request to all collections)
2. **`/graphql/async`** - Async endpoint (handles both hybrid and BM25, parallel requests using asyncio.gather)

## Implementation Details

The `/graphql/async` endpoint implements the same fanout pattern as `async_locust_hybrid_09.py`, but using `asyncio.gather` instead of gevent greenlets:

- **async_locust_hybrid_09.py**: Uses `gevent.spawn()` to create 9 greenlets, then `joinall()` to wait
- **fastapi_weaviate.py**: Uses `asyncio.gather()` to create 9 async tasks, then awaits them

Both approaches send 9 parallel GraphQL requests (one per collection) and wait for all to complete.

## Setup

1. Make sure dependencies are installed:
```bash
pip install fastapi uvicorn aiohttp pydantic
```

2. Ensure `config.py` exists in the parent directory (`weaviate-pt/`) with:
   - `WEAVIATE_URL` - Your Weaviate instance URL (e.g., `"http://20.161.96.75"`)
   - `WEAVIATE_API_KEY` - Your API key (if required)

## Running the FastAPI Server

From the `performance_testing/api/` directory:

```bash
cd performance_testing/api
uvicorn fastapi_weaviate:app --host 0.0.0.0 --port 8000 --reload
```

Or without reload:
```bash
uvicorn fastapi_weaviate:app --host 0.0.0.0 --port 8000
```

The API will be available at:
- API: `http://localhost:8000`
- Test endpoint: `http://localhost:8000/test` (verify connectivity)
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Testing Locust Connection to FastAPI

Before running full load tests, verify Locust can connect to FastAPI:

### Quick Connection Test

**Option 1: Simple Python test (no Locust required)**
```bash
cd performance_testing/api
python test_fastapi_connection.py

# Or with custom URL:
FASTAPI_URL=http://your-server:8000 python test_fastapi_connection.py
```
This tests all endpoints and shows a summary.

**Option 2: Using the bash script (includes Locust test)**
```bash
cd performance_testing/api
./test_connection.sh
```

**Option 3: Using Locust directly**
```bash
cd performance_testing/api
locust -f test_locust_connection.py --users 1 --spawn-rate 1 --run-time 10s --headless
```

**Option 4: Manual curl test**
```bash
# Test if FastAPI is running
curl http://localhost:8000/health

# Test comprehensive endpoint
curl http://localhost:8000/test
```

The test script will:
- Verify FastAPI is running
- Test all main endpoints
- Run a minimal Locust test (1 user, 10 seconds)
- Show connection status

## Testing with Locust

All Locust test files are located in `performance_testing/multi_collection/` directory.

### Test the Normal Hybrid Endpoint

From the `performance_testing/multi_collection/` directory:

```bash
locust -f locustfile_hybrid_09_fastapi.py --users 100 --spawn-rate 10 --run-time 5m --headless
```

### Test the Async Hybrid Endpoint

From the `performance_testing/multi_collection/` directory:

```bash
locust -f locustfile_hybrid_09_async_fastapi.py --users 100 --spawn-rate 10 --run-time 5m --headless
```

### Test the Normal BM25 Endpoint

From the `performance_testing/multi_collection/` directory:

```bash
locust -f locustfile_bm25_fastapi.py --users 100 --spawn-rate 10 --run-time 5m --headless
```

### Test the Async BM25 Endpoint

From the `performance_testing/multi_collection/` directory:

```bash
locust -f locustfile_bm25_async_fastapi.py --users 100 --spawn-rate 10 --run-time 5m --headless
```

### Set Custom FastAPI URL

If FastAPI is running on a different host/port:

```bash
FASTAPI_URL=http://your-server:8000 locust -f locustfile_hybrid_09_fastapi.py --users 100 --spawn-rate 10 --run-time 5m --headless
```

### Set Custom FastAPI URL

If FastAPI is running on a different host/port:

```bash
export FASTAPI_URL="http://your-server:8000"
locust -f locustfile_fastapi_async.py --users 100 --spawn-rate 10 --run-time 5m --headless
```

## Endpoint Usage

### 0. Test Endpoint (`/test`)

Comprehensive test endpoint that verifies FastAPI and Weaviate connectivity:

```bash
curl http://localhost:8000/test
```

**Response:**
```json
{
  "fastapi_status": "ok",
  "timestamp": 1234567890.123,
  "weaviate_url": "http://20.161.96.75",
  "weaviate_connection": {
    "status": "connected",
    "response_time_ms": 45.67,
    "status_code": 200
  },
  "weaviate_query_test": {
    "status": "success",
    "data_received": true
  },
  "collections_available": [
    "SongLyrics",
    "SongLyrics_400k",
    ...
  ],
  "errors": []
}
```

This endpoint tests:
- FastAPI service is running
- Connection to Weaviate works
- Can execute a simple GraphQL query
- Lists available collections

### 1. Normal GraphQL Endpoint (`/graphql`)

```bash
curl -X POST "http://localhost:8000/graphql" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ Get { SongLyrics(hybrid: { query: \"love\", alpha: 0.9, properties: [\"title\", \"lyrics\"] }, limit: 200) { title artist } } }"
  }'
```

### 2. Async Hybrid Endpoint (`/graphql/async`)

```bash
curl -X POST "http://localhost:8000/graphql/async" \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "love and heartbreak",
    "limit": 200,
    "alpha": 0.9
  }'
```

**Response:**
```json
{
  "query_text": "love and heartbreak",
  "limit": 200,
  "alpha": 0.9,
  "total_collections": 9,
  "successful_collections": 9,
  "failed_collections": 0,
  "total_time_ms": 245.67,
  "results": [
    {
      "collection": "SongLyrics",
      "status_code": 200,
      "data": { ... },
      "error": null
    },
    ...
  ]
}
```

### 3. Async BM25 Search (via `/graphql/async`)

To use BM25 search, omit the `alpha` parameter or set it to `0`:

```bash
curl -X POST "http://localhost:8000/graphql/async" \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "love and heartbreak",
    "limit": 200
  }'
```

**Response:**
```json
{
  "query_text": "love and heartbreak",
  "limit": 200,
  "alpha": 0.0,
  "total_collections": 9,
  "successful_collections": 9,
  "failed_collections": 0,
  "total_time_ms": 198.45,
  "results": [
    {
      "collection": "SongLyrics",
      "status_code": 200,
      "data": { ... },
      "error": null
    },
    ...
  ]
}
```

## How It Works

### Async Endpoint Flow (Hybrid and BM25)

1. **Request arrives** at `/graphql/async` with `query_text`, `limit`, and optional `alpha` parameter
2. **Task creation**: For each of the 9 collections:
   - Build a single-collection GraphQL query (hybrid or BM25)
   - Create an async task function (`search_one_collection_async`)
3. **Parallel execution**: Use `asyncio.gather(*tasks)` to execute all 9 tasks concurrently
4. **Wait for completion**: All tasks run in parallel, function returns when slowest completes
5. **Aggregate results**: Collect all results and return response

This is equivalent to:
- **Gevent approach**: `spawn()` 9 greenlets → `joinall()` wait
- **Async approach**: Create 9 async tasks → `asyncio.gather()` wait

Both achieve the same parallel execution pattern.

### Search Type Selection

The `/graphql/async` endpoint handles both search types based on the `alpha` parameter:

- **BM25 search**: Omit `alpha` or set `alpha=0` - Uses pure keyword search (no vector component)
- **Hybrid search**: Set `alpha` between 0 and 1 - Combines BM25 and vector search
  - `alpha=0`: Pure BM25 (same as omitting alpha)
  - `alpha=1`: Pure vector search
  - `alpha=0.9`: 90% vector, 10% BM25 (common hybrid configuration)

## Collections

The async endpoint queries these 9 collections in parallel:
- SongLyrics
- SongLyrics_400k
- SongLyrics_200k
- SongLyrics_50k
- SongLyrics_30k
- SongLyrics_20k
- SongLyrics_15k
- SongLyrics_12k
- SongLyrics_10k

## Notes

- The async endpoint uses `asyncio.gather` to send all collection queries in parallel
- Total latency is approximately the slowest collection query
- Both endpoints use the same Weaviate connection settings from `config.py`
- The API uses a shared `aiohttp.ClientSession` for efficient connection pooling
- All requests include `?consistency_level=ONE` parameter

