"""
Locust performance testing for FastAPI /graphql/async/lookup endpoint - Async GraphQL Lookup
Tests the async lookup endpoint that accepts query_text and looks up query_data.

Usage:
    locust -f locustfile_graphql_lookup_async.py --users 100 --spawn-rate 10 --run-time 5m --headless
    # Or set FASTAPI_URL environment variable:
    FASTAPI_URL=http://localhost:8000 locust -f locustfile_graphql_lookup_async.py --users 100 --spawn-rate 10 --run-time 5m --headless
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import json
import random
from locust import HttpUser, task, events
import config

QUERIES_HYBRID_09 = []


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Load Hybrid 0.9 query file when Locust starts"""
    global QUERIES_HYBRID_09
    
    print("=" * 70)
    print("Loading Hybrid (alpha=0.9) query file for FastAPI /graphql/async/lookup endpoint...")
    print("=" * 70)
    
    try:
        with open("queries/queries_hybrid_09_200.json", "r") as f:
            QUERIES_HYBRID_09 = json.load(f)
        print(f"✓ Loaded query file: {len(QUERIES_HYBRID_09)} queries")
        print(f"  Search type: Hybrid (alpha=0.9 - vector-focused)")
        print(f"  Target: FastAPI /graphql/async/lookup endpoint (async)")
        print(f"  Endpoint looks up query_data from query_text")
        print(f"  FastAPI fans out to 9 collections in parallel")
        print(f"  Returns aggregated results")
        print("=" * 70)
    except Exception as e:
        print(f"❌ Failed to load queries_hybrid_09_200.json: {e}")
        print("   Run: python ../../utilities/generate_all_queries.py --type multi --search-types hybrid_09 --limits 200")
        print("=" * 70)


class FastAPIGraphQLLookupAsyncUser(HttpUser):
    """
    Locust user that hits FastAPI /graphql/async/lookup endpoint.
    
    Each task:
      - Picks a random query from queries file
      - Sends POST to /graphql/async/lookup with only query_text
      - FastAPI looks up the full query_data from queries file
      - FastAPI extracts limit, vector, alpha from query_data
      - FastAPI fans out to 9 collections in parallel using asyncio.gather
      - Returns aggregated results
    """
    
    # Set FastAPI URL - defaults to weaviate-pt-test.shorthills.ai, can be overridden via FASTAPI_URL env var
    host = os.getenv("FASTAPI_URL", "https://weaviate-pt-test.shorthills.ai")
    
    def on_start(self):
        """Setup headers"""
        self.headers = {"Content-Type": "application/json"}
        # FastAPI doesn't need Weaviate auth headers - it handles them internally
    
    @task
    def search_graphql_lookup_async(self):
        """Execute GraphQL async lookup search via FastAPI /graphql/async/lookup endpoint"""
        if not QUERIES_HYBRID_09:
            return
        
        # Pick random query from queries
        query_data = random.choice(QUERIES_HYBRID_09)
        query_text = query_data["query_text"]
        
        # Build request payload - only query_text needed!
        payload = {
            "query_text": query_text,
            "query_file": "queries_hybrid_09_200.json"  # optional, defaults to this
        }
        
        # HTTP call with catch_response
        with self.client.post(
            "/graphql/async/lookup",
            headers=self.headers,
            json=payload,
            catch_response=True,
            name="FastAPI_GraphQL_Lookup_Async"
        ) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    # Check if FastAPI returned successful results
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

