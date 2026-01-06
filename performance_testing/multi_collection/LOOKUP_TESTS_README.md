# FastAPI Lookup Endpoints Performance Tests

This directory contains Locust performance tests for the FastAPI lookup endpoints that accept only `query_text` and automatically look up the full query data from the queries file.

## Endpoints Tested

### 1. `/graphql/lookup` (Sync)
- **Type**: Sync GraphQL endpoint
- **Locust File**: `locustfile_graphql_lookup_sync.py`
- **Behavior**: 
  - Accepts only `query_text`
  - Looks up GraphQL query from queries file
  - Single request to Weaviate (searches all 9 collections)
  - Returns Weaviate response directly

### 2. `/graphql/async/lookup` (Async)
- **Type**: Async endpoint with parallel collection requests
- **Locust File**: `locustfile_graphql_lookup_async.py`
- **Behavior**:
  - Accepts only `query_text`
  - Looks up query_data from queries file
  - Extracts limit, vector, alpha automatically
  - Parallel requests to 9 collections using asyncio.gather
  - Returns aggregated results

## Running the Tests

### Quick Start

```bash
cd performance_testing/multi_collection
./run_lookup_tests.sh
```

### Manual Execution

**Sync Lookup Test:**
```bash
FASTAPI_URL=https://weaviate-pt-test.shorthills.ai locust -f locustfile_graphql_lookup_sync.py \
    --users 100 \
    --spawn-rate 5 \
    --run-time 5m \
    --headless \
    --html reports/graphql_lookup_sync_report.html \
    --csv reports/graphql_lookup_sync
```

**Async Lookup Test:**
```bash
FASTAPI_URL=https://weaviate-pt-test.shorthills.ai locust -f locustfile_graphql_lookup_async.py \
    --users 100 \
    --spawn-rate 10 \
    --run-time 5m \
    --headless \
    --html reports/graphql_lookup_async_report.html \
    --csv reports/graphql_lookup_async
```

## Configuration

The shell script `run_lookup_tests.sh` supports the following environment variables:

- `FASTAPI_URL`: FastAPI server URL (default: `https://weaviate-pt-test.shorthills.ai`)
- `PT_RF_VALUE`: Replication factor value for report naming (default: `current`)

### Default Test Configuration

- **Users**: 100
- **Limit**: 200 results per collection
- **Spawn Rate**: 10 users/second
- **Duration**: 5 minutes per test
- **Query File**: `queries_hybrid_09_200.json`

### Customizing Test Parameters

Edit `run_lookup_tests.sh` to modify:
- `USER_COUNTS`: Array of user counts to test (e.g., `(10 50 100 200)`)
- `LIMIT`: Result limit per collection
- `SPAWN_RATE`: Users spawned per second
- `RUN_TIME`: Test duration (e.g., `"5m"`, `"10m"`)

## Report Generation

The script automatically generates:

1. **Individual Reports**: HTML and CSV files for each test
   - Location: `reports/multi_collection/fastapi_lookup_RF{RF_VALUE}_Users{COUNT}_Limit{LIMIT}/`
   - Files:
     - `graphql_lookup_sync_report.html`
     - `graphql_lookup_sync_stats.csv`
     - `graphql_lookup_async_report.html`
     - `graphql_lookup_async_stats.csv`

2. **Summary Report**: Combined HTML report with links to all individual reports
   - Location: `reports/multi_collection/fastapi_lookup_summary_RF{RF_VALUE}_Users{COUNT}_Limit{LIMIT}.html`

## Prerequisites

1. **Query Files**: Ensure query files exist in `queries/` directory
   ```bash
   # Generate if missing:
   python3 ../../utilities/generate_all_queries.py --type multi --search-types hybrid_09 --limits 200
   ```

2. **Locust**: Install Locust if not already installed
   ```bash
   pip install locust
   ```

3. **FastAPI Server**: Ensure FastAPI server is running and accessible

## Test Flow

1. **Load Queries**: Tests load `queries/queries_hybrid_09_200.json` at startup
2. **Random Selection**: Each task picks a random query from the loaded queries
3. **Send Request**: Sends POST request with only `query_text` (and optional `query_file`)
4. **Endpoint Processing**: FastAPI endpoint looks up full query data and processes the request
5. **Response Validation**: Validates response and marks success/failure

## Example Request Payload

```json
{
    "query_text": "love and heartbreak",
    "query_file": "queries_hybrid_09_200.json"
}
```

The `query_file` parameter is optional and defaults to `queries_hybrid_09_200.json`.

## Output Example

```
╔══════════════════════════════════════════════════════════════════════╗
║         FASTAPI LOOKUP ENDPOINTS PERFORMANCE TESTS                  ║
╚══════════════════════════════════════════════════════════════════════╝

Configuration:
  👥 Users: 100
  📊 Limit: 200
  🔄 RF: current
  🚀 Spawn Rate: 10 users/second
  ⏱️  Duration: 5m per test
  🌐 FastAPI URL: https://weaviate-pt-test.shorthills.ai

✅ Test complete: graphql_lookup_sync (Users: 100)
   📊 Report: ../reports/multi_collection/fastapi_lookup_RFcurrent_Users100_Limit200/graphql_lookup_sync_report.html
   📈 CSV: ../reports/multi_collection/fastapi_lookup_RFcurrent_Users100_Limit200/graphql_lookup_sync_stats.csv

✅ Test complete: graphql_lookup_async (Users: 100)
   📊 Report: ../reports/multi_collection/fastapi_lookup_RFcurrent_Users100_Limit200/graphql_lookup_async_report.html
   📈 CSV: ../reports/multi_collection/fastapi_lookup_RFcurrent_Users100_Limit200/graphql_lookup_async_stats.csv
```

## Troubleshooting

1. **Query file not found**: Ensure `queries/queries_hybrid_09_200.json` exists
2. **Connection errors**: Check `FASTAPI_URL` environment variable
3. **404 errors**: Verify query_text exists in the queries file
4. **Import errors**: Ensure you're running from `performance_testing/multi_collection/` directory

## Comparison with Other Endpoints

| Endpoint | Type | Request Format | Collections | Response |
|----------|------|----------------|-------------|----------|
| `/graphql/lookup` | Sync | `query_text` only | Single request (all 9) | Weaviate response |
| `/graphql/async/lookup` | Async | `query_text` only | Parallel (9 requests) | Aggregated results |
| `/graphql` | Sync | Full GraphQL query | Single request (all 9) | Weaviate response |
| `/graphql/async` | Async | `query_text`, `limit`, `alpha` | Parallel (9 requests) | Aggregated results |

The lookup endpoints simplify the request by requiring only `query_text`, while the regular endpoints require full parameters or GraphQL queries.

