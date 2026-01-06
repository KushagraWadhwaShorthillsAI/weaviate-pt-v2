"""
Locust performance testing for FastAPI /graphql endpoint - Hybrid Search (alpha=0.9)
Tests the normal GraphQL endpoint that forwards to Weaviate.

Usage:
    locust -f locustfile_hybrid_09_fastapi.py --users 100 --spawn-rate 5 --run-time 5m --headless
    # Or set FASTAPI_URL environment variable:
    FASTAPI_URL=http://localhost:8000 locust -f locustfile_hybrid_09_fastapi.py --users 100 --spawn-rate 5 --run-time 5m --headless
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
    print("Loading Hybrid (alpha=0.9) query file for FastAPI...")
    print("=" * 70)
    
    try:
        with open("queries/queries_hybrid_09_200.json", "r") as f:
            QUERIES_HYBRID_09 = json.load(f)
        print(f"✓ Loaded query file: {len(QUERIES_HYBRID_09)} queries")
        print(f"  Search type: Hybrid (alpha=0.9 - vector-focused)")
        print(f"  Target: FastAPI /graphql endpoint")
        print(f"  Each query searches 9 collections")
        print(f"  Returns 200 results per collection")
        print("=" * 70)
    except Exception as e:
        print(f"❌ Failed to load queries_hybrid_09.json: {e}")
        print("   Run: python ../../utilities/generate_all_queries.py --type multi --search-types hybrid_09")
        print("=" * 70)


class FastAPIHybrid09User(HttpUser):
    """Simulates a user performing Hybrid 0.9 searches via FastAPI"""
    
    # Set FastAPI URL - defaults to weaviate-pt-test.shorthills.ai, can be overridden via FASTAPI_URL env var
    host = os.getenv("FASTAPI_URL", "https://weaviate-pt-test.shorthills.ai")
    
    def on_start(self):
        """Setup headers"""
        self.headers = {"Content-Type": "application/json"}
        # FastAPI doesn't need Weaviate auth headers - it handles them internally
    
    @task
    def search_hybrid_09_all_collections(self):
        """Execute Hybrid (0.9) search via FastAPI /graphql endpoint"""
        if not QUERIES_HYBRID_09:
            return
        
        # Pick random query from 40 options
        query_data = random.choice(QUERIES_HYBRID_09)
        print(query_data)
        with open("dumped_query_data.json", "w") as outfile:
            json.dump(query_data, outfile, indent=2)
        
        # Send to FastAPI /graphql endpoint (which forwards to Weaviate)
        with self.client.post(
            "/graphql",
            headers=self.headers,
            json={"query": query_data["graphql"]},
            catch_response=True,
            name="FastAPI_Hybrid_0.9_Multi_Collection_Search"
        ) as response:
            if response.status_code == 200:
                result = response.json()
                if "errors" in result:
                    response.failure(f"GraphQL errors: {result['errors']}")
                else:
                    response.success()
            else:
                response.failure(f"HTTP {response.status_code}")

