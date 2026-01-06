# FastAPI Weaviate GraphQL API

REST API wrapper for Weaviate GraphQL queries with parallel request optimization.

## Quick Start

### 1. Start Server
```bash
cd performance_testing/api
uvicorn fastapi_weaviate:app --host 0.0.0.0 --port 8000
```

### 2. Test Connection
```bash
curl http://localhost:8000/test
```

### 3. Access API Docs
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Endpoints

### `/graphql`
Normal GraphQL endpoint - forwards single GraphQL query to Weaviate.

**Request:**
```json
{
  "query": "{ Get { SongLyrics(hybrid: {...}) {...} } }"
}
```

### `/graphql/async`
Async endpoint - parallel requests to 9 collections.

**Request:**
```json
{
  "query_text": "love and heartbreak",
  "limit": 200,
  "alpha": 0.9
}
```

**Response:**
```json
{
  "total_time_ms": 245.67,
  "successful_collections": 9,
  "results": [...]
}
```

### `/graphql/lookup`
Sync endpoint with query lookup from queries file.

**Request:**
```json
{
  "query_text": "love and heartbreak"
}
```

### `/graphql/async/lookup`
Async endpoint with query lookup.

**Request:**
```json
{
  "query_text": "love and heartbreak"
}
```

## Search Types

- **BM25:** Omit `alpha` or set `alpha=0`
- **Hybrid:** Set `alpha` between 0 and 1
  - `alpha=0.9`: 90% vector, 10% BM25
  - `alpha=0.1`: 10% vector, 90% BM25

## Testing with Locust

```bash
cd ../multi_collection
locust -f locustfile_hybrid_09_fastapi.py --users 100 --spawn-rate 10 --run-time 5m --headless
```

## Configuration

Ensure `config.py` exists in project root with:
- `WEAVIATE_URL` - Weaviate instance URL
- `WEAVIATE_API_KEY` - API key (if required)

## Collections

Queries 9 collections in parallel:
- SongLyrics, SongLyrics_400k, SongLyrics_200k, SongLyrics_50k, SongLyrics_30k, SongLyrics_20k, SongLyrics_15k, SongLyrics_12k, SongLyrics_10k
