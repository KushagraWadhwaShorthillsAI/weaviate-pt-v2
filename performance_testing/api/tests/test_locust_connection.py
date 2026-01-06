"""
Quick test script to verify Locust can connect to FastAPI.
This runs a minimal test with just 1 user for a few seconds.

Usage:
    cd performance_testing/api
    python test_locust_connection.py
    
Or run directly with Locust:
    cd performance_testing/api
    locust -f test_locust_connection.py --users 1 --spawn-rate 1 --run-time 10s --headless
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from locust import HttpUser, task
import os

class FastAPIConnectionTest(HttpUser):
    """
    Minimal test to verify Locust can connect to FastAPI.
    Tests all main endpoints with simple requests.
    """
    
    # Set FastAPI URL - defaults to localhost:8000
    host = os.getenv("FASTAPI_URL", "http://localhost:8000")
    
    def on_start(self):
        """Setup headers."""
        self.headers = {"Content-Type": "application/json"}
        print(f"\n{'='*70}")
        print(f"Testing connection to FastAPI at: {self.host}")
        print(f"{'='*70}\n")
    
    @task(3)
    def test_root_endpoint(self):
        """Test root endpoint."""
        with self.client.get("/", name="Root_Endpoint", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
                print("✓ Root endpoint (/): OK")
            else:
                response.failure(f"HTTP {response.status_code}")
                print(f"✗ Root endpoint (/): FAILED - HTTP {response.status_code}")
    
    @task(3)
    def test_health_endpoint(self):
        """Test health endpoint."""
        with self.client.get("/health", name="Health_Endpoint", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
                print("✓ Health endpoint (/health): OK")
            else:
                response.failure(f"HTTP {response.status_code}")
                print(f"✗ Health endpoint (/health): FAILED - HTTP {response.status_code}")
    
    @task(2)
    def test_test_endpoint(self):
        """Test comprehensive test endpoint."""
        with self.client.get("/test", name="Test_Endpoint", catch_response=True) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    status = result.get("fastapi_status", "unknown")
                    weaviate_status = result.get("weaviate_connection", {}).get("status", "unknown")
                    response.success()
                    print(f"✓ Test endpoint (/test): FastAPI={status}, Weaviate={weaviate_status}")
                except Exception as e:
                    response.failure(f"JSON parsing error: {str(e)}")
                    print(f"✗ Test endpoint (/test): JSON parsing failed - {str(e)}")
            else:
                response.failure(f"HTTP {response.status_code}")
                print(f"✗ Test endpoint (/test): FAILED - HTTP {response.status_code}")
    
    @task(1)
    def test_graphql_endpoint(self):
        """Test GraphQL endpoint with simple query."""
        simple_query = """
        {
          Get {
            SongLyrics(limit: 1) {
              title
            }
          }
        }
        """
        with self.client.post(
            "/graphql",
            headers=self.headers,
            json={"query": simple_query},
            name="GraphQL_Endpoint",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    if "errors" in result:
                        response.failure(f"GraphQL errors: {result['errors']}")
                        print(f"✗ GraphQL endpoint (/graphql): GraphQL errors: {result['errors']}")
                    else:
                        response.success()
                        print("✓ GraphQL endpoint (/graphql): OK")
                except Exception as e:
                    response.failure(f"JSON parsing error: {str(e)}")
                    print(f"✗ GraphQL endpoint (/graphql): JSON parsing failed - {str(e)}")
            else:
                response.failure(f"HTTP {response.status_code}")
                print(f"✗ GraphQL endpoint (/graphql): FAILED - HTTP {response.status_code}")
    
    @task(1)
    def test_async_endpoint(self):
        """Test async endpoint with simple query."""
        payload = {
            "query_text": "love",
            "limit": 10,
            "alpha": 0.9
        }
        with self.client.post(
            "/graphql/async",
            headers=self.headers,
            json=payload,
            name="Async_Endpoint",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    successful = result.get("successful_collections", 0)
                    if successful > 0:
                        response.success()
                        print(f"✓ Async endpoint (/graphql/async): OK ({successful}/9 collections)")
                    else:
                        response.failure(f"No successful collections")
                        print(f"✗ Async endpoint (/graphql/async): No successful collections")
                except Exception as e:
                    response.failure(f"JSON parsing error: {str(e)}")
                    print(f"✗ Async endpoint (/graphql/async): JSON parsing failed - {str(e)}")
            else:
                response.failure(f"HTTP {response.status_code}")
                print(f"✗ Async endpoint (/graphql/async): FAILED - HTTP {response.status_code}")

