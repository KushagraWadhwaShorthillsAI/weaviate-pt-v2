"""
Locust performance testing for FastAPI /graphql/lookup endpoint - Sync GraphQL Lookup (BM25)
Tests the sync lookup endpoint with BM25 queries.

Usage:
    locust -f locustfile_graphql_lookup_sync_bm25.py --users 100 --spawn-rate 5 --run-time 5m --headless
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import json
import random
from locust import HttpUser, task, events
import config

QUERIES_BM25 = []


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Load BM25 query file when Locust starts"""
    global QUERIES_BM25
    
    print("=" * 70)
    print("Loading BM25 query file for FastAPI /graphql/lookup endpoint...")
    print("=" * 70)
    
    try:
        with open("queries/queries_bm25_200.json", "r") as f:
            QUERIES_BM25 = json.load(f)
        print(f"✓ Loaded query file: {len(QUERIES_BM25)} queries")
        print(f"  Search type: BM25 (keyword-only)")
        print(f"  Target: FastAPI /graphql/lookup endpoint (sync)")
        print(f"  Endpoint looks up GraphQL query from query_text")
        print(f"  Each query searches 9 collections in single request")
        print(f"  Returns 200 results per collection")
        print("=" * 70)
    except Exception as e:
        print(f"❌ Failed to load queries_bm25_200.json: {e}")
        print("   Run: python ../../utilities/generate_all_queries.py --type multi --search-types bm25 --limits 200")
        print("=" * 70)


class FastAPIGraphQLLookupSyncBM25User(HttpUser):
    """Locust user that hits FastAPI /graphql/lookup endpoint with BM25 queries"""
    
    host = os.getenv("FASTAPI_URL", "https://weaviate-pt-test.shorthills.ai")
    
    def on_start(self):
        """Setup headers"""
        self.headers = {"Content-Type": "application/json"}
    
    @task
    def search_graphql_lookup_sync_bm25(self):
        """Execute BM25 GraphQL lookup search via FastAPI /graphql/lookup endpoint"""
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
        
        # Send to FastAPI /graphql/lookup endpoint
        with self.client.post(
            "/graphql/lookup",
            headers=self.headers,
            json=payload,
            catch_response=True,
            name="FastAPI_GraphQL_Lookup_Sync_BM25"
        ) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    if "errors" in result:
                        response.failure(f"GraphQL errors: {result['errors']}")
                    else:
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

