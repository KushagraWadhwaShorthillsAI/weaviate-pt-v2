"""
Locust performance testing for FastAPI /graphql/lookup endpoint - Sync GraphQL Lookup
Tests the sync lookup endpoint that accepts query_text and looks up the GraphQL query.

Usage:
    locust -f locustfile_graphql_lookup_sync.py --users 100 --spawn-rate 5 --run-time 5m --headless
    # Or set FASTAPI_URL environment variable:
    FASTAPI_URL=http://localhost:8000 locust -f locustfile_graphql_lookup_sync.py --users 100 --spawn-rate 5 --run-time 5m --headless
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
    print("Loading Hybrid (alpha=0.9) query file for FastAPI /graphql/lookup endpoint...")
    print("=" * 70)
    
    try:
        with open("queries/queries_hybrid_09_200.json", "r") as f:
            QUERIES_HYBRID_09 = json.load(f)
        print(f"✓ Loaded query file: {len(QUERIES_HYBRID_09)} queries")
        print(f"  Search type: Hybrid (alpha=0.9 - vector-focused)")
        print(f"  Target: FastAPI /graphql/lookup endpoint (sync)")
        print(f"  Endpoint looks up GraphQL query from query_text")
        print(f"  Each query searches 9 collections in single request")
        print(f"  Returns 200 results per collection")
        print("=" * 70)
    except Exception as e:
        print(f"❌ Failed to load queries_hybrid_09_200.json: {e}")
        print("   Run: python ../../utilities/generate_all_queries.py --type multi --search-types hybrid_09 --limits 200")
        print("=" * 70)


class FastAPIGraphQLLookupSyncUser(HttpUser):
    """
    Locust user that hits FastAPI /graphql/lookup endpoint (sync).
    
    Each task:
      - Picks a random query from queries file
      - Sends POST to /graphql/lookup with only query_text
      - FastAPI looks up the full GraphQL query from queries file
      - FastAPI forwards GraphQL query to Weaviate (single request)
      - Returns Weaviate response directly
    """
    
    # Set FastAPI URL - defaults to weaviate-pt-test.shorthills.ai, can be overridden via FASTAPI_URL env var
    host = os.getenv("FASTAPI_URL", "https://weaviate-pt-test.shorthills.ai")
    
    def on_start(self):
        """Setup headers"""
        self.headers = {"Content-Type": "application/json"}
        # FastAPI doesn't need Weaviate auth headers - it handles them internally
    
    @task
    def search_graphql_lookup_sync(self):
        """Execute GraphQL lookup search via FastAPI /graphql/lookup endpoint"""
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
        
        # Send to FastAPI /graphql/lookup endpoint
        with self.client.post(
            "/graphql/lookup",
            headers=self.headers,
            json=payload,
            catch_response=True,
            name="FastAPI_GraphQL_Lookup_Sync"
        ) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    # Check for GraphQL errors
                    if "errors" in result:
                        response.failure(f"GraphQL errors: {result['errors']}")
                    else:
                        # Check if we got data back
                        if "data" in result and result["data"]:
                            response.success()
                        else:
                            response.failure("No data in response")
                except Exception as e:
                    response.failure(f"Failed to parse JSON: {e}")
            elif response.status_code == 404:
                response.failure(f"Query text not found: {query_text}")
            else:
                response.failure(f"HTTP {response.status_code}")

