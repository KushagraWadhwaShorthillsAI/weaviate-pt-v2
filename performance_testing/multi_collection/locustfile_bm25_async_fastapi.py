"""
Locust performance testing for FastAPI /graphql/async endpoint - BM25 Search Only
Tests the async endpoint with BM25 search (alpha=None) that fans out to 9 collections in parallel using asyncio.gather.

Usage:
    locust -f locustfile_bm25_async_fastapi.py --users 100 --spawn-rate 10 --run-time 5m --headless
    # Or set FASTAPI_URL environment variable:
    FASTAPI_URL=http://localhost:8000 locust -f locustfile_bm25_async_fastapi.py --users 100 --spawn-rate 10 --run-time 5m --headless
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
    """Load BM25 query file when Locust starts."""
    global QUERIES_BM25

    print("=" * 70)
    print("Loading BM25 query file for FastAPI async endpoint...")
    print("=" * 70)

    queries_path = os.path.join("queries", "queries_bm25_200.json")

    try:
        with open(queries_path, "r") as f:
            QUERIES_BM25 = json.load(f)
        print(f"✓ Loaded query file: {len(QUERIES_BM25)} queries")
        print(f"  Search type: BM25 (pure keyword search)")
        print(f"  Target: FastAPI /graphql/async endpoint (with alpha=None for BM25)")
        print(f"  FastAPI will fan out to 9 collections in parallel")
        print("=" * 70)
    except Exception as e:
        print(f"❌ Failed to load {queries_path}: {e}")
        print("=" * 70)


class FastAPIBM25AsyncUser(HttpUser):
    """
    Locust user that hits FastAPI /graphql/async endpoint with BM25 search.
    
    Each task:
      - Picks a random BM25 query (query_text + limit)
      - Sends POST to /graphql/async with query_text, limit (no alpha parameter for BM25)
      - FastAPI internally fans out to 9 collections using asyncio.gather
      - Returns aggregated results
    """

    # Set FastAPI URL - defaults to weaviate-pt-test.shorthills.ai, can be overridden via FASTAPI_URL env var
    host = os.getenv("FASTAPI_URL", "https://weaviate-pt-test.shorthills.ai")

    def on_start(self):
        """Setup headers."""
        self.headers = {"Content-Type": "application/json"}
        # FastAPI doesn't need Weaviate auth headers - it handles them internally

    @task
    def search_bm25_all_collections_async(self):
        """
        Fan-out via FastAPI: one logical query → FastAPI handles 9 concurrent collection requests.
        This models: "user waits for slowest collection, while all collections
        are searched in parallel by FastAPI".
        """
        if not QUERIES_BM25:
            return

        query_data = random.choice(QUERIES_BM25)
        query_text = query_data["query_text"]
        limit = query_data.get("limit", 200)

        # Send to FastAPI /graphql/async endpoint (no alpha parameter = BM25 search)
        # FastAPI will handle the fanout internally
        with self.client.post(
            "/graphql/async",
            headers=self.headers,
            json={
                "query_text": query_text,
                "limit": limit
            },
            catch_response=True,
            name="FastAPI_BM25_Async_Fanout"
        ) as response:
            if response.status_code == 200:
                result = response.json()
                # Check if FastAPI returned successful results
                if result.get("successful_collections", 0) > 0:
                    response.success()
                else:
                    response.failure(f"No successful collections: {result}")
            else:
                response.failure(f"HTTP {response.status_code}")

