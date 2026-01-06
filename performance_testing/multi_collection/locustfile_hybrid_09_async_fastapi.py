"""
Locust performance testing for FastAPI /graphql/async endpoint - Hybrid Search (alpha=0.9)
Async Locust user hitting an async FastAPI endpoint that fans out to 9 collections
in parallel using asyncio.gather.

Usage:
    locust -f locustfile_hybrid_09_async_fastapi_aio.py --users 100 --spawn-rate 10 --run-time 5m --headless
    # Or set FASTAPI_URL environment variable:
    FASTAPI_URL=http://localhost:8000 locust -f locustfile_hybrid_09_async_fastapi_aio.py --users 100 --spawn-rate 10 --run-time 5m --headless
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import json
import random
import re
from locust import AsyncHttpUser, task, events
import config  # if you need anything from here

QUERIES_HYBRID_09 = []


def extract_vector_from_graphql(graphql_str: str) -> list | None:
    """Extract vector array from GraphQL query string."""
    match = re.search(r'vector:\s*(\[)', graphql_str)
    if match:
        start_pos = match.end(1) - 1  # position of opening bracket
        bracket_count = 0
        end_pos = start_pos

        # Find the matching closing bracket
        for i in range(start_pos, len(graphql_str)):
            if graphql_str[i] == '[':
                bracket_count += 1
            elif graphql_str[i] == ']':
                bracket_count -= 1
                if bracket_count == 0:
                    end_pos = i + 1
                    break

        if bracket_count == 0:
            try:
                vector_str = graphql_str[start_pos:end_pos]
                return json.loads(vector_str)
            except json.JSONDecodeError:
                return None
    return None


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Load Hybrid 0.9 query file when Locust starts."""
    global QUERIES_HYBRID_09

    print("=" * 70)
    print("Loading Hybrid (alpha=0.9) query file for FastAPI async endpoint...")
    print("=" * 70)

    queries_path = os.path.join("queries", "queries_hybrid_09_200.json")

    try:
        with open(queries_path, "r") as f:
            QUERIES_HYBRID_09 = json.load(f)
        print(f"✓ Loaded query file: {len(QUERIES_HYBRID_09)} queries")
        print("  Search type: Hybrid (alpha=0.9 - vector-focused)")
        print("  Target: FastAPI /graphql/async endpoint")
        print("  FastAPI will fan out to 9 collections in parallel")
        print("=" * 70)
    except Exception as e:
        print(f"❌ Failed to load {queries_path}: {e}")
        print("=" * 70)


class FastAPIHybrid09AsyncUser(AsyncHttpUser):
    """
    Async Locust user that hits FastAPI /graphql/async endpoint.

    Each task:
      - Picks a random hybrid_09 query (query_text + limit)
      - Sends POST to /graphql/async with query_text, limit, alpha (and optional vector)
      - FastAPI internally fans out to 9 collections using asyncio.gather
      - Returns aggregated results
    """

    # Set FastAPI URL - defaults to weaviate-pt-test.shorthills.ai, can be overridden via FASTAPI_URL env var
    host = os.getenv("FASTAPI_URL", "https://weaviate-pt-test.shorthills.ai")

    # Optional: define wait_time if you want think time
    # from locust import between
    # wait_time = between(0.1, 1.0)

    def on_start(self):
        """Setup headers."""
        self.headers = {"Content-Type": "application/json"}
        # FastAPI doesn't need Weaviate auth headers - it handles them internally

    @task
    async def search_hybrid_09_all_collections_async(self):
        """
        Fan-out via FastAPI: one logical query → FastAPI handles 9 concurrent collection requests.

        This models: "user waits for slowest collection, while all collections
        are searched in parallel by FastAPI", and we use async HTTP client on Locust side.
        """
        if not QUERIES_HYBRID_09:
            return

        query_data = random.choice(QUERIES_HYBRID_09)
        print(f"Selected query_data: {query_data}")

        # Debug dump (blocking file I/O, but OK for small test / can be removed in heavy runs)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_file = os.path.join(script_dir, "dumped_query_data.json")
        try:
            with open(output_file, "w") as outfile:
                json.dump(query_data, outfile, indent=2)
            print(f"✓ Query data dumped to: {output_file}")
        except Exception as e:
            print(f"❌ Failed to dump query data to {output_file}: {e}")

        query_text = query_data["query_text"]
        limit = query_data.get("limit", 200)

        # Extract vector from the GraphQL query in the queries file
        graphql_query = query_data.get("graphql", "")
        query_vector = extract_vector_from_graphql(graphql_query)

        # Build request payload
        payload = {
            "query_text": query_text,
            "limit": limit,
            "alpha": 0.9,
        }

        # Add vector if extracted successfully
        if query_vector:
            payload["vector"] = query_vector

        print("=" * 70)
        print("REQUEST PAYLOAD:")
        print(json.dumps(payload, indent=2))
        print("=" * 70)

        # Async HTTP call with catch_response
        async with self.client.post(
            "/graphql/async",
            headers=self.headers,
            json=payload,
            catch_response=True,
            name="FastAPI_Hybrid_0.9_Async_Fanout",
        ) as response:
            # status_code & json() are provided by Locust's response wrapper
            if response.status_code == 200:
                try:
                    result = response.json()
                except Exception as e:
                    response.failure(f"Failed to parse JSON: {e}")
                    return

                if result.get("successful_collections", 0) > 0:
                    response.success()
                else:
                    response.failure(f"No successful collections: {result}")
            else:
                response.failure(f"HTTP {response.status_code}")
