"""
Locust performance testing for FastAPI /graphql/async/lookup endpoint - Async GraphQL Lookup (BM25)
Tests the async lookup endpoint with BM25 queries.

Usage:
    locust -f locustfile_graphql_lookup_async_bm25.py --users 100 --spawn-rate 10 --run-time 5m --headless
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import json
import random
from locust import AsyncHttpUser, task, events
import config

QUERIES_BM25 = []


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Load BM25 query file when Locust starts"""
    global QUERIES_BM25
    
    print("=" * 70)
    print("Loading BM25 query file for FastAPI /graphql/async/lookup endpoint...")
    print("=" * 70)
    
    try:
        with open("queries/queries_bm25_200.json", "r") as f:
            QUERIES_BM25 = json.load(f)
        print(f"✓ Loaded query file: {len(QUERIES_BM25)} queries")
        print(f"  Search type: BM25 (keyword-only)")
        print(f"  Target: FastAPI /graphql/async/lookup endpoint (async)")
        print(f"  Endpoint looks up query_data from query_text")
        print(f"  FastAPI fans out to 9 collections in parallel")
        print(f"  Returns aggregated results")
        print("=" * 70)
    except Exception as e:
        print(f"❌ Failed to load queries_bm25_200.json: {e}")
        print("   Run: python ../../utilities/generate_all_queries.py --type multi --search-types bm25 --limits 200")
        print("=" * 70)


class FastAPIGraphQLLookupAsyncBM25User(AsyncHttpUser):
    """Async Locust user that hits FastAPI /graphql/async/lookup endpoint with BM25 queries"""
    
    host = os.getenv("FASTAPI_URL", "https://weaviate-pt-test.shorthills.ai")
    
    def on_start(self):
        """Setup headers"""
        self.headers = {"Content-Type": "application/json"}
    
    @task
    async def search_graphql_lookup_async_bm25(self):
        """Execute BM25 GraphQL async lookup search via FastAPI /graphql/async/lookup endpoint"""
        if not QUERIES_BM25:
            return
        
        # Pick random query from queries
        query_data = random.choice(QUERIES_BM25)
        query_text = query_data["query_text"]
        
        # Build request payload - specify BM25 query file
        payload = {
            "query_text": query_text,
            "query_file": "queries_bm25_200.json"
        }
        
        # Async HTTP call with catch_response
        async with self.client.post(
            "/graphql/async/lookup",
            headers=self.headers,
            json=payload,
            catch_response=True,
            name="FastAPI_GraphQL_Lookup_Async_BM25"
        ) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    if result.get("successful_collections", 0) > 0:
                        response.success()
                    else:
                        response.failure(f"No successful collections: {result}")
                except Exception as e:
                    response.failure(f"Failed to parse JSON: {e}")
            elif response.status_code == 404:
                response.failure(f"Query text not found: {query_text}")
            else:
                response.failure(f"HTTP {response.status_code}")

