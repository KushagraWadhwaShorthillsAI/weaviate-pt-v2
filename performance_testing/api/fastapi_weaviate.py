"""
FastAPI application for Weaviate GraphQL queries with endpoints:
1. /graphql - Normal GraphQL endpoint (single request to all collections)
2. /graphql/async - Async endpoint (handles both hybrid and BM25, parallel requests to individual collections using asyncio.gather)

Usage:
    cd performance_testing/api
    uvicorn fastapi_weaviate:app --host 0.0.0.0 --port 8000
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import asyncio
import logging
import time 
import json
import re
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import aiohttp
import config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('fastapi_weaviate.log')
    ]
)
logger = logging.getLogger(__name__)

# Same 9 collections as your multi-collection setup
MULTI_COLLECTIONS = [
    "SongLyrics", "SongLyrics_400k", "SongLyrics_200k",
    "SongLyrics_50k", "SongLyrics_30k", "SongLyrics_20k",
    "SongLyrics_15k", "SongLyrics_12k", "SongLyrics_10k",
]

app = FastAPI(
    title="Weaviate GraphQL API",
    description="GraphQL endpoints for Weaviate with normal and async modes",
    version="1.0.0"
)

# Global aiohttp session (reused across requests)
_session: Optional[aiohttp.ClientSession] = None


def get_headers() -> Dict[str, str]:
    """Build headers for Weaviate requests."""
    headers = {"Content-Type": "application/json"}
    if config.WEAVIATE_API_KEY and config.WEAVIATE_API_KEY != "your-weaviate-api-key":
        headers["Authorization"] = f"Bearer {config.WEAVIATE_API_KEY}"
    return headers


def extract_vector_from_graphql(graphql_str: str) -> Optional[List[float]]:
    """Extract vector array from GraphQL query string."""
    if not graphql_str:
        return None
    
    # Try to find vector: [ ... ] pattern
    # Look for "vector:" followed by whitespace and opening bracket
    match = re.search(r'vector:\s*(\[)', graphql_str, re.IGNORECASE)
    if match:
        start_pos = match.end(1) - 1  # Position of opening bracket [
        bracket_count = 0
        end_pos = start_pos
        
        # Find the matching closing bracket - handle large vectors (3072 dimensions)
        for i in range(start_pos, len(graphql_str)):
            char = graphql_str[i]
            if char == '[':
                bracket_count += 1
            elif char == ']':
                bracket_count -= 1
                if bracket_count == 0:
                    end_pos = i + 1
                    break
        
        if bracket_count == 0 and end_pos > start_pos:
            try:
                vector_str = graphql_str[start_pos:end_pos]
                vector = json.loads(vector_str)
                # Validate it's a list of numbers
                if isinstance(vector, list) and len(vector) > 0:
                    return vector
            except (json.JSONDecodeError, ValueError) as e:
                logger.debug(f"Failed to parse vector from GraphQL: {e}")
                return None
    
    return None


def load_queries_from_file(query_file: str) -> List[Dict[str, Any]]:
    """Load queries from JSON file."""
    # Try multiple possible paths
    possible_paths = [
        os.path.join(os.path.dirname(__file__), "../multi_collection/queries", query_file),
        os.path.join(os.path.dirname(__file__), "../../performance_testing/multi_collection/queries", query_file),
        query_file,  # Try as absolute path
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    queries = json.load(f)
                logger.info(f"Loaded {len(queries)} queries from {path}")
                return queries
            except Exception as e:
                logger.error(f"Failed to load queries from {path}: {e}")
                continue
    
    raise FileNotFoundError(f"Query file not found: {query_file}. Tried paths: {possible_paths}")


def find_query_by_text(query_text: str, query_file: str = "queries_hybrid_09_200.json") -> Optional[Dict[str, Any]]:
    """Find query data by query_text from queries file."""
    try:
        queries = load_queries_from_file(query_file)
        for query_data in queries:
            if query_data.get("query_text") == query_text:
                return query_data
        return None
    except Exception as e:
        logger.error(f"Error finding query: {e}")
        return None


def build_single_collection_hybrid_graphql(
    query_text: str,
    collection: str,
    alpha: float,
    limit: int,
    query_vector: Optional[List[float]] = None,
) -> str:
    """
    Build a single-collection Hybrid (alpha) GraphQL query.
    Mirrors your generator, but scoped to one collection.
    
    If query_vector is provided, includes it in the hybrid query.
    This is required when collections don't have a vectorizer configured.
    """
    escaped = query_text.replace('"', '\\"')
    
    # Build hybrid query parameters
    hybrid_params = f'query: "{escaped}"\n        alpha: {alpha}'
    
    # Add vector if provided
    if query_vector is not None:
        import json
        vector_str = json.dumps(query_vector)
        hybrid_params += f'\n        vector: {vector_str}'
    
    hybrid_params += '\n        properties: ["title", "lyrics"]'

    return f"""
{{
  Get {{
    {collection}(
      hybrid: {{
        {hybrid_params}
      }}
      limit: {limit}
    ) {{
      title
      tag
      artist
      year
      views
      features
      lyrics
      song_id
      language_cld3
      language_ft
      language
      _additional {{
        score
      }}
    }}
  }}
}}
""".strip()


def build_single_collection_bm25_graphql(
    query_text: str,
    collection: str,
    limit: int,
) -> str:
    """
    Build a single-collection BM25 GraphQL query.
    Mirrors your generator, but scoped to one collection.
    """
    escaped = query_text.replace('"', '\\"')

    return f"""
{{
  Get {{
    {collection}(
      bm25: {{
        query: "{escaped}"
        properties: ["title", "lyrics"]
      }}
      limit: {limit}
    ) {{
      title
      tag
      artist
      year
      views
      features
      lyrics
      song_id
      language_cld3
      language_ft
      language
      _additional {{
        score
      }}
    }}
  }}
}}
""".strip()


@app.on_event("startup")
async def startup_event():
    """Initialize aiohttp session on startup."""
    global _session
    logger.info("=" * 80)
    logger.info("FastAPI Weaviate API - Starting up")
    logger.info(f"Weaviate URL: {config.WEAVIATE_URL}")
    logger.info(f"Collections configured: {len(MULTI_COLLECTIONS)}")
    logger.info(f"Collections: {', '.join(MULTI_COLLECTIONS)}")
    _session = aiohttp.ClientSession()
    logger.info("✓ aiohttp session initialized")
    logger.info("=" * 80)


@app.on_event("shutdown")
async def shutdown_event():
    """Close aiohttp session on shutdown."""
    global _session
    logger.info("=" * 80)
    logger.info("FastAPI Weaviate API - Shutting down")
    if _session:
        await _session.close()
        logger.info("✓ aiohttp session closed")
    logger.info("=" * 80)


# ============================================================================
# Request/Response Models
# ============================================================================

class GraphQLRequest(BaseModel):
    """Request model for normal GraphQL endpoint."""
    query: Optional[str] = Field(None, description="GraphQL query string (required if query_text not provided)")
    query_text: Optional[str] = Field(None, description="Query text to look up from queries file (required if query not provided)")
    query_file: Optional[str] = Field(default="queries_hybrid_09_200.json", description="Query file name for lookup (only used with query_text)")


class AsyncRequest(BaseModel):
    """Request model for async endpoint (handles both hybrid and BM25)."""
    query_text: str = Field(..., description="Search query text")
    limit: int = Field(default=200, ge=1, le=1000, description="Number of results per collection")
    alpha: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Hybrid search alpha (None or 0=BM25, >0=hybrid with alpha, 1=vector)")
    vector: Optional[List[float]] = Field(default=None, description="Query vector embedding (required for hybrid search when collections don't have vectorizer)")


class QueryTextRequest(BaseModel):
    """Request model for query_text lookup endpoint."""
    query_text: str = Field(..., description="Search query text to look up in queries file")
    query_file: Optional[str] = Field(default="queries_hybrid_09_200.json", description="Query file name (default: queries_hybrid_09_200.json)")


class CollectionResult(BaseModel):
    """Result from a single collection."""
    collection: str
    status_code: int
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class AsyncResponse(BaseModel):
    """Response model for async endpoint (handles both hybrid and BM25)."""
    query_text: str
    limit: int
    alpha: float  # Will be 0.0 for BM25 queries
    total_collections: int
    successful_collections: int
    failed_collections: int
    results: List[CollectionResult]
    total_time_ms: float


# ============================================================================
# Endpoints
# ============================================================================

@app.post("/graphql", response_model=Dict[str, Any])
async def graphql_normal(request: GraphQLRequest):
    """
    Normal GraphQL endpoint - forwards a single GraphQL query to Weaviate.
    
    This endpoint accepts either:
    1. A full GraphQL query string in the "query" field
    2. A query_text that will be looked up from the queries file
    
    Examples:
        # Direct GraphQL query
        POST /graphql
        {
            "query": "{ Get { SongLyrics(hybrid: {...}) {...} } }"
        }
        
        # Query text lookup
        POST /graphql
        {
            "query_text": "love and heartbreak",
            "query_file": "queries_hybrid_09_200.json"  # optional
        }
    """
    request_id = id(request)
    start_time = time.perf_counter()
    logger.info(f"[REQ-{request_id}] POST /graphql - Received GraphQL request")
    
    # Validate that at least one of query or query_text is provided
    if not request.query and not request.query_text:
        error_msg = "Either 'query' (GraphQL query string) or 'query_text' (to look up from queries file) must be provided"
        logger.error(f"[REQ-{request_id}] {error_msg}")
        raise HTTPException(status_code=400, detail=error_msg)
    
    # If query_text is provided, look it up from the queries file
    graphql_query = request.query
    if request.query_text:
        logger.info(f"[REQ-{request_id}] Looking up query_text: '{request.query_text}' from {request.query_file}")
        query_data = find_query_by_text(request.query_text, request.query_file)
        
        if not query_data:
            error_msg = f"Query text '{request.query_text}' not found in {request.query_file}"
            logger.error(f"[REQ-{request_id}] {error_msg}")
            raise HTTPException(status_code=404, detail=error_msg)
        
        # Extract GraphQL query from query_data
        graphql_query = query_data.get("graphql", "")
        
        if not graphql_query:
            error_msg = f"No GraphQL query found in query_data for '{request.query_text}'"
            logger.error(f"[REQ-{request_id}] {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        logger.info(f"[REQ-{request_id}] ✓ Found query_data: limit={query_data.get('limit', 200)}")
    
    # Validate that we have a GraphQL query
    if not graphql_query:
        error_msg = "No GraphQL query available. Provide either 'query' or 'query_text'."
        logger.error(f"[REQ-{request_id}] {error_msg}")
        raise HTTPException(status_code=400, detail=error_msg)
    
    logger.debug(f"[REQ-{request_id}] Query length: {len(graphql_query)} characters")
    
    if not _session:
        logger.error(f"[REQ-{request_id}] HTTP session not initialized")
        raise HTTPException(status_code=500, detail="HTTP session not initialized")
    
    # Build URL with consistency_level parameter
    base_url = config.WEAVIATE_URL.rstrip('/')
    url = f"{base_url}/v1/graphql?consistency_level=ONE"
    headers = get_headers()
    payload = {"query": graphql_query}
    
    logger.debug(f"[REQ-{request_id}] Sending request to Weaviate: {url}")
    
    # Set timeout for the request (30 seconds default)
    timeout = aiohttp.ClientTimeout(total=30)
    
    try:
        async with _session.post(url, headers=headers, json=payload, timeout=timeout) as resp:
            status_code = resp.status
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            
            logger.info(f"[REQ-{request_id}] Weaviate response status: {status_code} (took {elapsed_ms:.2f}ms)")
            
            try:
                result = await resp.json()
            except Exception as json_error:
                logger.error(f"[REQ-{request_id}] Failed to parse JSON response: {str(json_error)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to parse JSON response: {str(json_error)}"
                )
            
            if status_code != 200:
                logger.error(f"[REQ-{request_id}] Weaviate returned error status {status_code}: {result}")
                raise HTTPException(
                    status_code=status_code,
                    detail=f"Weaviate returned status {status_code}: {result}"
                )
            
            # Check for GraphQL errors
            if "errors" in result:
                logger.error(f"[REQ-{request_id}] GraphQL errors in response: {result['errors']}")
                raise HTTPException(
                    status_code=400,
                    detail=f"GraphQL errors: {result['errors']}"
                )
            
            # Log success
            data_keys = list(result.get("data", {}).keys()) if isinstance(result.get("data"), dict) else []
            logger.info(f"[REQ-{request_id}] ✓ Request completed successfully (total: {elapsed_ms:.2f}ms)")
            logger.debug(f"[REQ-{request_id}] Response data keys: {data_keys}")
            
            return result
            
    except asyncio.TimeoutError:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.error(f"[REQ-{request_id}] Request timeout after {elapsed_ms:.2f}ms")
        raise HTTPException(
            status_code=504,
            detail="Request to Weaviate timed out (30s exceeded)"
        )
    except aiohttp.ClientError as e:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.error(f"[REQ-{request_id}] HTTP client error after {elapsed_ms:.2f}ms: {str(e)}")
        raise HTTPException(status_code=500, detail=f"HTTP client error: {str(e)}")
    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.error(f"[REQ-{request_id}] Unexpected error after {elapsed_ms:.2f}ms: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.post("/graphql/lookup", response_model=Dict[str, Any])
async def graphql_lookup(request: QueryTextRequest):
    """
    GraphQL sync endpoint with query_text lookup.
    
    This endpoint accepts only query_text and looks up the full query_data
    (including GraphQL query) from the queries file, then forwards it to Weaviate.
    
    Example:
        POST /graphql/lookup
        {
            "query_text": "love and heartbreak",
            "query_file": "queries_hybrid_09_200.json"  # optional, defaults to queries_hybrid_09_200.json
        }
    
    The endpoint will:
    1. Look up the query_data by query_text from the queries file
    2. Extract the GraphQL query from query_data["graphql"]
    3. Forward the GraphQL query to Weaviate (same as /graphql endpoint)
    4. Return the Weaviate response
    """
    request_id = f"LOOKUP-SYNC-{int(time.time() * 1000)}"
    start_time = time.perf_counter()
    
    logger.info("=" * 80)
    logger.info(f"[REQ-{request_id}] POST /graphql/lookup - Query text lookup (sync)")
    logger.info(f"[REQ-{request_id}] Query text: '{request.query_text}'")
    logger.info(f"[REQ-{request_id}] Query file: '{request.query_file}'")
    
    # Look up query_data from queries file
    query_data = find_query_by_text(request.query_text, request.query_file)
    
    if not query_data:
        error_msg = f"Query text '{request.query_text}' not found in {request.query_file}"
        logger.error(f"[REQ-{request_id}] {error_msg}")
        raise HTTPException(status_code=404, detail=error_msg)
    
    # Extract GraphQL query from query_data
    graphql_query = query_data.get("graphql", "")
    
    if not graphql_query:
        error_msg = f"No GraphQL query found in query_data for '{request.query_text}'"
        logger.error(f"[REQ-{request_id}] {error_msg}")
        raise HTTPException(status_code=400, detail=error_msg)
    
    logger.info(f"[REQ-{request_id}] ✓ Found query_data: limit={query_data.get('limit', 200)}")
    logger.debug(f"[REQ-{request_id}] GraphQL query length: {len(graphql_query)} characters")
    
    # Build GraphQLRequest and call the existing graphql_normal logic
    graphql_request = GraphQLRequest(query=graphql_query)
    
    # Reuse the graphql_normal endpoint logic
    if not _session:
        logger.error(f"[REQ-{request_id}] HTTP session not initialized")
        raise HTTPException(status_code=500, detail="HTTP session not initialized")
    
    # Build URL with consistency_level parameter
    base_url = config.WEAVIATE_URL.rstrip('/')
    url = f"{base_url}/v1/graphql?consistency_level=ONE"
    headers = get_headers()
    payload = {"query": graphql_request.query}
    
    logger.debug(f"[REQ-{request_id}] Sending request to Weaviate: {url}")
    
    # Set timeout for the request (30 seconds default)
    timeout = aiohttp.ClientTimeout(total=30)
    
    try:
        async with _session.post(url, headers=headers, json=payload, timeout=timeout) as resp:
            status_code = resp.status
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            
            logger.info(f"[REQ-{request_id}] Weaviate response status: {status_code} (took {elapsed_ms:.2f}ms)")
            
            try:
                result = await resp.json()
            except Exception as json_error:
                logger.error(f"[REQ-{request_id}] Failed to parse JSON response: {str(json_error)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to parse JSON response: {str(json_error)}"
                )
            
            if status_code != 200:
                logger.error(f"[REQ-{request_id}] Weaviate returned error status {status_code}: {result}")
                raise HTTPException(
                    status_code=status_code,
                    detail=f"Weaviate returned status {status_code}: {result}"
                )
            
            # Check for GraphQL errors
            if "errors" in result:
                logger.error(f"[REQ-{request_id}] GraphQL errors in response: {result['errors']}")
                raise HTTPException(
                    status_code=400,
                    detail=f"GraphQL errors: {result['errors']}"
                )
            
            # Log success
            data_keys = list(result.get("data", {}).keys()) if isinstance(result.get("data"), dict) else []
            logger.info(f"[REQ-{request_id}] ✓ Request completed successfully (total: {elapsed_ms:.2f}ms)")
            logger.info(f"[REQ-{request_id}] Response data keys: {data_keys}")
            logger.info("=" * 80)
            
            return result
            
    except asyncio.TimeoutError:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.error(f"[REQ-{request_id}] Request timeout after {elapsed_ms:.2f}ms")
        raise HTTPException(
            status_code=504,
            detail="Request to Weaviate timed out (30s exceeded)"
        )
    except aiohttp.ClientError as e:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.error(f"[REQ-{request_id}] HTTP client error after {elapsed_ms:.2f}ms: {str(e)}")
        raise HTTPException(status_code=500, detail=f"HTTP client error: {str(e)}")
    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.error(f"[REQ-{request_id}] Unexpected error after {elapsed_ms:.2f}ms: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


async def search_one_collection_async(
    session: aiohttp.ClientSession,
    collection: str,
    graphql_query: str,
    request_id: Optional[str] = None,
) -> CollectionResult:
    """
    Task function: Execute a single-collection GraphQL query asynchronously.
    
    This function is called for each collection and runs in parallel via asyncio.gather.
    Similar to how gevent spawns greenlets in async_locust_hybrid_09.py, but using
    asyncio instead of gevent.
    
    Returns CollectionResult with status and data/error.
    
    This function handles all exceptions internally and always returns a CollectionResult,
    ensuring that asyncio.gather can collect all results even if some collections fail.
    """
    task_id = f"{request_id}-{collection}" if request_id else collection
    task_start = time.perf_counter()
    logger.debug(f"[TASK-{task_id}] Starting async task for collection: {collection}")
    
    # Build URL with consistency_level parameter
    base_url = config.WEAVIATE_URL.rstrip('/')
    url = f"{base_url}/v1/graphql?consistency_level=ONE"
    headers = get_headers()
    payload = {"query": graphql_query}
    
    # Set timeout for the request (30 seconds default)
    timeout = aiohttp.ClientTimeout(total=30)
    
    try:
        logger.debug(f"[TASK-{task_id}] Sending request to Weaviate")
        async with session.post(url, headers=headers, json=payload, timeout=timeout) as resp:
            status_code = resp.status
            task_elapsed = (time.perf_counter() - task_start) * 1000
            
            if status_code == 200:
                try:
                    result = await resp.json()
                    if "errors" in result:
                        logger.warning(f"[TASK-{task_id}] GraphQL errors in response (took {task_elapsed:.2f}ms): {result['errors']}")
                        return CollectionResult(
                            collection=collection,
                            status_code=status_code,
                            error=f"GraphQL errors: {result['errors']}"
                        )
                    # Count results if available
                    result_count = 0
                    if isinstance(result.get("data"), dict):
                        for key, value in result["data"].items():
                            if isinstance(value, list):
                                result_count = len(value)
                                break
                    logger.info(f"[TASK-{task_id}] ✓ Completed successfully (took {task_elapsed:.2f}ms, {result_count} results)")
                    return CollectionResult(
                        collection=collection,
                        status_code=status_code,
                        data=result
                    )
                except Exception as json_error:
                    # Handle JSON parsing errors
                    logger.error(f"[TASK-{task_id}] JSON parsing error (took {task_elapsed:.2f}ms): {str(json_error)}")
                    return CollectionResult(
                        collection=collection,
                        status_code=status_code,
                        error=f"JSON parsing error: {str(json_error)}"
                    )
            else:
                try:
                    text = await resp.text()
                    logger.warning(f"[TASK-{task_id}] HTTP error {status_code} (took {task_elapsed:.2f}ms): {text[:200]}")
                    return CollectionResult(
                        collection=collection,
                        status_code=status_code,
                        error=f"HTTP {status_code}: {text[:200]}"
                    )
                except Exception as text_error:
                    logger.error(f"[TASK-{task_id}] Failed to read error response (took {task_elapsed:.2f}ms): {str(text_error)}")
                    return CollectionResult(
                        collection=collection,
                        status_code=status_code,
                        error=f"HTTP {status_code}: Failed to read response ({str(text_error)})"
                    )
                
    except asyncio.TimeoutError:
        task_elapsed = (time.perf_counter() - task_start) * 1000
        logger.error(f"[TASK-{task_id}] Request timeout after {task_elapsed:.2f}ms")
        return CollectionResult(
            collection=collection,
            status_code=0,
            error="Request timeout (30s exceeded)"
        )
    except aiohttp.ClientError as e:
        task_elapsed = (time.perf_counter() - task_start) * 1000
        logger.error(f"[TASK-{task_id}] HTTP client error after {task_elapsed:.2f}ms: {str(e)}")
        return CollectionResult(
            collection=collection,
            status_code=0,
            error=f"HTTP client error: {str(e)}"
        )
    except Exception as e:
        task_elapsed = (time.perf_counter() - task_start) * 1000
        logger.error(f"[TASK-{task_id}] Unexpected exception after {task_elapsed:.2f}ms: {str(e)}", exc_info=True)
        return CollectionResult(
            collection=collection,
            status_code=0,
            error=f"Unexpected exception: {str(e)}"
        )

@app.post("/graphql/async", response_model=AsyncResponse)
async def graphql_async(request: AsyncRequest):
    """
    Async GraphQL endpoint - divides query into separate collection queries
    and sends them in parallel using asyncio.gather.
    
    This endpoint handles BOTH hybrid and BM25 queries:
    - If alpha is None or 0: Uses BM25 search (pure keyword search)
    - If alpha > 0: Uses hybrid search with the specified alpha value
    
    This endpoint:
    1. Takes query_text, limit, and optional alpha
    2. Builds one GraphQL query per collection (9 total) - either hybrid or BM25
    3. Creates a task function for each collection
    4. Sends all 9 queries in parallel using asyncio.gather
    5. Returns aggregated results
    
    This is equivalent to async_locust_hybrid_09.py's fanout approach, but using
    asyncio.gather instead of gevent greenlets.
    
    Examples:
        # Hybrid search (alpha=0.9)
        POST /graphql/async
        {
            "query_text": "love and heartbreak",
            "limit": 200,
            "alpha": 0.9
        }
        
        # BM25 search (alpha=None or alpha=0)
        POST /graphql/async
        {
            "query_text": "love and heartbreak",
            "limit": 200
        }
    """
    request_id = f"ASYNC-{int(time.time() * 1000)}"
    start_time = time.perf_counter()
    
    logger.info("=" * 80)
    logger.info(f"[REQ-{request_id}] POST /graphql/async - Received async request")
    logger.info(f"[REQ-{request_id}] Query text: '{request.query_text}'")
    logger.info(f"[REQ-{request_id}] Limit: {request.limit}")
    logger.info(f"[REQ-{request_id}] Alpha: {request.alpha} (None/0 = BM25, >0 = Hybrid)")
    
    if not _session:
        logger.error(f"[REQ-{request_id}] HTTP session not initialized")
        raise HTTPException(status_code=500, detail="HTTP session not initialized")
    
    # Determine search type: BM25 if alpha is None or 0, otherwise hybrid
    # CRITICAL: This ensures clear segregation - no mixing between BM25 and hybrid
    use_bm25 = request.alpha is None or request.alpha == 0.0
    # Set alpha value: 0.0 for BM25, otherwise use the provided alpha (default to 0.9 if somehow None)
    alpha_value = 0.0 if use_bm25 else (request.alpha if request.alpha is not None else 0.9)
    
    # Explicit validation to prevent mixing
    if use_bm25 and alpha_value > 0:
        logger.error(f"[REQ-{request_id}] ERROR: BM25 query detected but alpha_value > 0: {alpha_value}")
        raise HTTPException(status_code=400, detail=f"Invalid configuration: BM25 query cannot have alpha > 0")
    if not use_bm25 and alpha_value == 0.0:
        logger.error(f"[REQ-{request_id}] ERROR: Hybrid query detected but alpha_value == 0.0")
        raise HTTPException(status_code=400, detail=f"Invalid configuration: Hybrid query must have alpha > 0")
    
    search_type = "BM25" if use_bm25 else f"Hybrid (alpha={alpha_value})"
    logger.info(f"[REQ-{request_id}] Search type: {search_type}")
    logger.info(f"[REQ-{request_id}] Query type segregation: use_bm25={use_bm25}, alpha_value={alpha_value}")
    logger.info(f"[REQ-{request_id}] Creating {len(MULTI_COLLECTIONS)} parallel tasks (one per collection)")
    
    # Build tasks for all collections - each task is a separate async function call
    # This mirrors the gevent spawn pattern: one task per collection
    tasks = []
    task_creation_start = time.perf_counter()
    for collection in MULTI_COLLECTIONS:
        if use_bm25:
            # Use BM25 query - CRITICAL: Only BM25 queries use this path
            logger.debug(f"[REQ-{request_id}] Building BM25 query for {collection}")
            graphql = build_single_collection_bm25_graphql(
                query_text=request.query_text,
                collection=collection,
                limit=request.limit,
            )
            # Runtime validation: Verify BM25 query contains 'bm25:' and NOT 'hybrid:'
            if "bm25:" not in graphql.lower():
                logger.error(f"[REQ-{request_id}] ERROR: BM25 query missing 'bm25:' keyword: {graphql[:200]}")
                raise HTTPException(status_code=500, detail="BM25 query validation failed: missing 'bm25:' keyword")
            if "hybrid:" in graphql.lower():
                logger.error(f"[REQ-{request_id}] ERROR: BM25 query incorrectly contains 'hybrid:' keyword: {graphql[:200]}")
                raise HTTPException(status_code=500, detail="BM25 query validation failed: contains 'hybrid:' keyword")
        else:
            # Use hybrid query - CRITICAL: Only hybrid queries use this path
            logger.debug(f"[REQ-{request_id}] Building Hybrid query (alpha={alpha_value}) for {collection}")
            graphql = build_single_collection_hybrid_graphql(
                query_text=request.query_text,
                collection=collection,
                alpha=alpha_value,
                limit=request.limit,
                query_vector=request.vector,
            )
            # Runtime validation: Verify hybrid query contains 'hybrid:' and NOT 'bm25:'
            if "hybrid:" not in graphql.lower():
                logger.error(f"[REQ-{request_id}] ERROR: Hybrid query missing 'hybrid:' keyword: {graphql[:200]}")
                raise HTTPException(status_code=500, detail="Hybrid query validation failed: missing 'hybrid:' keyword")
            if "bm25:" in graphql.lower():
                logger.error(f"[REQ-{request_id}] ERROR: Hybrid query incorrectly contains 'bm25:' keyword: {graphql[:200]}")
                raise HTTPException(status_code=500, detail="Hybrid query validation failed: contains 'bm25:' keyword")
        # Create async task for this collection using create_task for explicit task creation
        # Equivalent to: g = spawn(self._do_request, collection, graphql) in gevent
        # Using create_task ensures tasks are scheduled immediately and can be tracked
        logger.debug(f"[REQ-{request_id}] Creating task for collection: {collection}")
        task = asyncio.create_task(
            search_one_collection_async(_session, collection, graphql, request_id=request_id)
        )
        tasks.append(task)
    
    task_creation_time = (time.perf_counter() - task_creation_start) * 1000
    logger.info(f"[REQ-{request_id}] ✓ Created {len(tasks)} tasks in {task_creation_time:.2f}ms")
    logger.info(f"[REQ-{request_id}] Starting parallel execution with asyncio.gather...")
    
    # Execute all tasks in parallel using asyncio.gather
    # Equivalent to: joinall(greenlets) in gevent
    # return_exceptions=True ensures we get all results even if some fail
    # (though search_one_collection_async catches exceptions internally)
    gather_start = time.perf_counter()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    gather_time = (time.perf_counter() - gather_start) * 1000
    logger.info(f"[REQ-{request_id}] ✓ All tasks completed in {gather_time:.2f}ms (parallel execution)")
    
    # Handle any unexpected exceptions that might have escaped
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            # This shouldn't happen since search_one_collection_async catches all exceptions,
            # but handle it defensively
            logger.error(f"[REQ-{request_id}] Unexpected exception from task {i} ({MULTI_COLLECTIONS[i]}): {str(result)}")
            processed_results.append(
                CollectionResult(
                    collection=MULTI_COLLECTIONS[i],
                    status_code=0,
                    error=f"Unexpected exception: {str(result)}"
                )
            )
        else:
            processed_results.append(result)
    results = processed_results
    
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    
    # Count successes and failures
    successful = sum(1 for r in results if r.status_code == 200)
    failed = len(results) - successful
    
    # Log detailed results summary
    logger.info(f"[REQ-{request_id}] Results summary:")
    logger.info(f"[REQ-{request_id}]   - Total collections: {len(MULTI_COLLECTIONS)}")
    logger.info(f"[REQ-{request_id}]   - Successful: {successful}")
    logger.info(f"[REQ-{request_id}]   - Failed: {failed}")
    logger.info(f"[REQ-{request_id}]   - Total time: {elapsed_ms:.2f}ms")
    logger.info(f"[REQ-{request_id}]   - Parallel execution time: {gather_time:.2f}ms")
    
    # Log individual collection results
    for result in results:
        if result.status_code == 200:
            result_count = 0
            if isinstance(result.data, dict):
                for key, value in result.data.items():
                    if isinstance(value, list):
                        result_count = len(value)
                        break
            logger.debug(f"[REQ-{request_id}]   ✓ {result.collection}: {result_count} results")
        else:
            logger.warning(f"[REQ-{request_id}]   ✗ {result.collection}: {result.error}")
    
    logger.info(f"[REQ-{request_id}] ✓ Request completed successfully")
    logger.info("=" * 80)
    
    return AsyncResponse(
        query_text=request.query_text,
        limit=request.limit,
        alpha=alpha_value if not use_bm25 else 0.0,
        total_collections=len(MULTI_COLLECTIONS),
        successful_collections=successful,
        failed_collections=failed,
        results=results,
        total_time_ms=elapsed_ms
    )


@app.post("/graphql/async/lookup", response_model=AsyncResponse)
async def graphql_async_lookup(request: QueryTextRequest):
    """
    Async GraphQL endpoint with query_text lookup.
    
    This endpoint accepts only query_text and looks up the full query_data
    (including limit, vector, etc.) from the queries file.
    
    Example:
        POST /graphql/async/lookup
        {
            "query_text": "love and heartbreak",
            "query_file": "queries_hybrid_09_200.json"  # optional, defaults to queries_hybrid_09_200.json
        }
    
    The endpoint will:
    1. Look up the query_data by query_text from the queries file
    2. Extract limit, vector, and other metadata from query_data
    3. Use the full query_data to execute the search
    """
    request_id = f"LOOKUP-{int(time.time() * 1000)}"
    start_time = time.perf_counter()
    
    logger.info("=" * 80)
    logger.info(f"[REQ-{request_id}] POST /graphql/async/lookup - Query text lookup")
    logger.info(f"[REQ-{request_id}] Query text: '{request.query_text}'")
    logger.info(f"[REQ-{request_id}] Query file: '{request.query_file}'")
    
    # Look up query_data from queries file
    query_data = find_query_by_text(request.query_text, request.query_file)
    
    if not query_data:
        error_msg = f"Query text '{request.query_text}' not found in {request.query_file}"
        logger.error(f"[REQ-{request_id}] {error_msg}")
        raise HTTPException(status_code=404, detail=error_msg)
    
    logger.info(f"[REQ-{request_id}] ✓ Found query_data: limit={query_data.get('limit', 200)}")
    
    # Extract data from query_data
    query_text = query_data["query_text"]
    limit = query_data.get("limit", 200)
    graphql_query = query_data.get("graphql", "")  # Get GraphQL query for later use
    
    # Extract vector - try direct vector field first, then from GraphQL query
    query_vector = query_data.get("vector")
    logger.debug(f"[REQ-{request_id}] Direct vector field: {'found' if query_vector is not None else 'not found'}")
    
    if query_vector is None:
        logger.debug(f"[REQ-{request_id}] Attempting to extract vector from GraphQL query (length: {len(graphql_query)})")
        query_vector = extract_vector_from_graphql(graphql_query)
        logger.debug(f"[REQ-{request_id}] Vector extraction: {'success' if query_vector is not None else 'failed'}")
        if query_vector is not None:
            logger.debug(f"[REQ-{request_id}] Extracted vector length: {len(query_vector)}")
    
    # Determine query type first (BM25 vs Hybrid)
    is_bm25_query = False
    if "bm25" in request.query_file.lower():
        is_bm25_query = True
        logger.debug(f"[REQ-{request_id}] Detected BM25 query from filename")
    elif graphql_query and "bm25:" in graphql_query.lower():
        is_bm25_query = True
        logger.debug(f"[REQ-{request_id}] Detected BM25 query from GraphQL structure")
    
    # For hybrid queries, vector is REQUIRED (collections don't have vectorizers)
    if not is_bm25_query:
        if query_vector is None:
            error_msg = f"Vector is required for hybrid queries but not found in query_data for '{request.query_text}'. Collections don't have vectorizers configured. Please ensure the query file contains vector data."
            logger.error(f"[REQ-{request_id}] {error_msg}")
            logger.error(f"[REQ-{request_id}] GraphQL query length: {len(graphql_query)}")
            logger.error(f"[REQ-{request_id}] GraphQL query preview: {graphql_query[:500]}...")
            raise HTTPException(status_code=400, detail=error_msg)
        logger.info(f"[REQ-{request_id}] ✓ Vector found for hybrid query: length={len(query_vector)}")
    
    if is_bm25_query:
        # BM25 queries don't use alpha (or alpha=0)
        alpha = None  # None means BM25 in the async endpoint
    else:
        # For hybrid queries, get alpha from query_data or default based on query_file
        alpha = query_data.get("alpha")
        if alpha is None:
            # Default based on query_file name
            if "hybrid_01" in request.query_file.lower():
                alpha = 0.1
            elif "hybrid_09" in request.query_file.lower():
                alpha = 0.9
            else:
                alpha = 0.9  # Default to hybrid_09
    
    # Build AsyncRequest from query_data
    async_request = AsyncRequest(
        query_text=query_text,
        limit=limit,
        alpha=alpha,
        vector=query_vector
    )
    
    logger.info(f"[REQ-{request_id}] Using query_data: limit={limit}, alpha={alpha}, has_vector={query_vector is not None}")
    
    # Call the existing graphql_async endpoint logic
    # We'll reuse the same logic but with the looked-up data
    if not _session:
        logger.error(f"[REQ-{request_id}] HTTP session not initialized")
        raise HTTPException(status_code=500, detail="HTTP session not initialized")
    
    # Determine search type: BM25 if alpha is None or 0, otherwise hybrid
    # CRITICAL: This ensures clear segregation - no mixing between BM25 and hybrid
    use_bm25 = async_request.alpha is None or async_request.alpha == 0.0
    alpha_value = 0.0 if use_bm25 else (async_request.alpha if async_request.alpha is not None else 0.9)
    
    # Explicit validation to prevent mixing
    if use_bm25 and alpha_value > 0:
        logger.error(f"[REQ-{request_id}] ERROR: BM25 query detected but alpha_value > 0: {alpha_value}")
        raise HTTPException(status_code=400, detail=f"Invalid configuration: BM25 query cannot have alpha > 0")
    if not use_bm25 and alpha_value == 0.0:
        logger.error(f"[REQ-{request_id}] ERROR: Hybrid query detected but alpha_value == 0.0")
        raise HTTPException(status_code=400, detail=f"Invalid configuration: Hybrid query must have alpha > 0")
    
    search_type = "BM25" if use_bm25 else f"Hybrid (alpha={alpha_value})"
    logger.info(f"[REQ-{request_id}] Search type: {search_type}")
    logger.info(f"[REQ-{request_id}] Query type segregation: use_bm25={use_bm25}, alpha_value={alpha_value}")
    logger.info(f"[REQ-{request_id}] Creating {len(MULTI_COLLECTIONS)} parallel tasks (one per collection)")
    
    # Build tasks for all collections
    tasks = []
    task_creation_start = time.perf_counter()
    for collection in MULTI_COLLECTIONS:
        if use_bm25:
            # Use BM25 query - CRITICAL: Only BM25 queries use this path
            logger.debug(f"[REQ-{request_id}] Building BM25 query for {collection}")
            graphql = build_single_collection_bm25_graphql(
                query_text=async_request.query_text,
                collection=collection,
                limit=async_request.limit,
            )
            # Runtime validation: Verify BM25 query contains 'bm25:' and NOT 'hybrid:'
            if "bm25:" not in graphql.lower():
                logger.error(f"[REQ-{request_id}] ERROR: BM25 query missing 'bm25:' keyword: {graphql[:200]}")
                raise HTTPException(status_code=500, detail="BM25 query validation failed: missing 'bm25:' keyword")
            if "hybrid:" in graphql.lower():
                logger.error(f"[REQ-{request_id}] ERROR: BM25 query incorrectly contains 'hybrid:' keyword: {graphql[:200]}")
                raise HTTPException(status_code=500, detail="BM25 query validation failed: contains 'hybrid:' keyword")
        else:
            # Use hybrid query - CRITICAL: Only hybrid queries use this path
            logger.debug(f"[REQ-{request_id}] Building Hybrid query (alpha={alpha_value}) for {collection}")
            graphql = build_single_collection_hybrid_graphql(
                query_text=async_request.query_text,
                collection=collection,
                alpha=alpha_value,
                limit=async_request.limit,
                query_vector=async_request.vector,
            )
            # Runtime validation: Verify hybrid query contains 'hybrid:' and NOT 'bm25:'
            if "hybrid:" not in graphql.lower():
                logger.error(f"[REQ-{request_id}] ERROR: Hybrid query missing 'hybrid:' keyword: {graphql[:200]}")
                raise HTTPException(status_code=500, detail="Hybrid query validation failed: missing 'hybrid:' keyword")
            if "bm25:" in graphql.lower():
                logger.error(f"[REQ-{request_id}] ERROR: Hybrid query incorrectly contains 'bm25:' keyword: {graphql[:200]}")
                raise HTTPException(status_code=500, detail="Hybrid query validation failed: contains 'bm25:' keyword")
        logger.debug(f"[REQ-{request_id}] Creating task for collection: {collection}")
        task = asyncio.create_task(
            search_one_collection_async(_session, collection, graphql, request_id=request_id)
        )
        tasks.append(task)
    
    task_creation_time = (time.perf_counter() - task_creation_start) * 1000
    logger.info(f"[REQ-{request_id}] ✓ Created {len(tasks)} tasks in {task_creation_time:.2f}ms")
    logger.info(f"[REQ-{request_id}] Starting parallel execution with asyncio.gather...")
    
    # Execute all tasks in parallel
    gather_start = time.perf_counter()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    gather_time = (time.perf_counter() - gather_start) * 1000
    
    # Convert exceptions to CollectionResult with error
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            processed_results.append(CollectionResult(
                collection=MULTI_COLLECTIONS[i],
                status_code=500,
                data=None,
                error=str(result)
            ))
        else:
            processed_results.append(result)
    
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    
    successful = sum(1 for r in processed_results if r.status_code == 200)
    failed = len(processed_results) - successful
    
    logger.info(f"[REQ-{request_id}] Results summary:")
    logger.info(f"[REQ-{request_id}]   - Total collections: {len(MULTI_COLLECTIONS)}")
    logger.info(f"[REQ-{request_id}]   - Successful: {successful}")
    logger.info(f"[REQ-{request_id}]   - Failed: {failed}")
    logger.info(f"[REQ-{request_id}]   - Total time: {elapsed_ms:.2f}ms")
    logger.info(f"[REQ-{request_id}] ✓ Request completed successfully")
    logger.info("=" * 80)
    
    return AsyncResponse(
        query_text=async_request.query_text,
        limit=async_request.limit,
        alpha=alpha_value if not use_bm25 else 0.0,
        total_collections=len(MULTI_COLLECTIONS),
        successful_collections=successful,
        failed_collections=failed,
        results=processed_results,
        total_time_ms=elapsed_ms
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "weaviate_url": config.WEAVIATE_URL}


@app.get("/test")
async def test_endpoint():
    """
    Comprehensive test endpoint that verifies:
    1. FastAPI service is running
    2. Connection to Weaviate is working
    3. Can execute a simple GraphQL query
    
    Returns detailed status information for debugging.
    """
    import time
    test_results = {
        "fastapi_status": "ok",
        "timestamp": time.time(),
        "weaviate_url": config.WEAVIATE_URL,
        "weaviate_connection": None,
        "weaviate_query_test": None,
        "collections_available": [],
        "errors": []
    }
    
    # Test 1: Check if session is initialized
    if not _session:
        test_results["errors"].append("HTTP session not initialized")
        test_results["fastapi_status"] = "error"
        return test_results
    
    # Test 2: Try to connect to Weaviate
    base_url = config.WEAVIATE_URL.rstrip('/')
    url = f"{base_url}/v1/graphql?consistency_level=ONE"
    headers = get_headers()
    
    # Simple test query - just check if Weaviate responds
    test_query = """
    {
      Get {
        SongLyrics(limit: 1) {
          title
        }
      }
    }
    """
    
    try:
        # Test connection
        start_time = time.perf_counter()
        async with _session.post(url, headers=headers, json={"query": test_query}, timeout=aiohttp.ClientTimeout(total=5)) as resp:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            status_code = resp.status
            
            if status_code == 200:
                result = await resp.json()
                test_results["weaviate_connection"] = {
                    "status": "connected",
                    "response_time_ms": round(elapsed_ms, 2),
                    "status_code": status_code
                }
                
                # Check if query executed successfully
                if "errors" in result:
                    test_results["weaviate_query_test"] = {
                        "status": "error",
                        "error": result["errors"]
                    }
                    test_results["errors"].append(f"GraphQL errors: {result['errors']}")
                else:
                    test_results["weaviate_query_test"] = {
                        "status": "success",
                        "data_received": True
                    }
            else:
                text = await resp.text()
                test_results["weaviate_connection"] = {
                    "status": "error",
                    "status_code": status_code,
                    "error": text[:200]
                }
                test_results["errors"].append(f"Weaviate returned HTTP {status_code}")
                
    except asyncio.TimeoutError:
        test_results["weaviate_connection"] = {
            "status": "timeout",
            "error": "Connection to Weaviate timed out"
        }
        test_results["errors"].append("Connection timeout to Weaviate")
    except Exception as e:
        test_results["weaviate_connection"] = {
            "status": "error",
            "error": str(e)
        }
        test_results["errors"].append(f"Connection error: {str(e)}")
    
    # Test 3: Try to get schema info (list collections)
    try:
        schema_url = f"{base_url}/v1/schema"
        async with _session.get(schema_url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as resp:
            if resp.status == 200:
                schema_data = await resp.json()
                if "classes" in schema_data:
                    test_results["collections_available"] = [cls.get("class", "") for cls in schema_data.get("classes", [])]
    except Exception:
        # Schema check is optional, don't fail if it doesn't work
        pass
    
    # Overall status
    if test_results["errors"]:
        test_results["fastapi_status"] = "partial" if test_results["weaviate_connection"] and test_results["weaviate_connection"].get("status") == "connected" else "error"
    else:
        test_results["fastapi_status"] = "ok"
    
    return test_results


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Weaviate GraphQL API",
        "endpoints": {
            "/graphql": "Normal GraphQL endpoint (single request to all collections)",
            "/graphql/lookup": "GraphQL sync endpoint with query_text lookup (accepts only query_text, looks up GraphQL query from queries file)",
            "/graphql/async": "Async endpoint (handles both hybrid and BM25 based on alpha parameter, parallel requests to individual collections)",
            "/graphql/async/lookup": "Async endpoint with query_text lookup (accepts only query_text, looks up full query_data from queries file)",
            "/health": "Health check",
            "/test": "Comprehensive test endpoint (verifies FastAPI and Weaviate connectivity)",
            "/docs": "API documentation (Swagger UI)"
        }
    }

