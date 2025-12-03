#!/usr/bin/env python3
"""
Simple script to test FastAPI connection without Locust.
Useful for quick verification before running load tests.

Usage:
    cd performance_testing/api
    python test_fastapi_connection.py
    
    # Or with custom URL:
    FASTAPI_URL=http://your-server:8000 python test_fastapi_connection.py
"""

import sys
import os
import requests
import json

# Get FastAPI URL from environment or use default
FASTAPI_URL = os.getenv("FASTAPI_URL", "http://localhost:8000")

def test_endpoint(name, method, url, **kwargs):
    """Test a single endpoint and return result."""
    try:
        if method.upper() == "GET":
            response = requests.get(url, timeout=5, **kwargs)
        elif method.upper() == "POST":
            response = requests.post(url, timeout=5, **kwargs)
        else:
            return False, f"Unsupported method: {method}"
        
        if response.status_code == 200:
            return True, response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
        else:
            return False, f"HTTP {response.status_code}: {response.text[:200]}"
    except requests.exceptions.ConnectionError:
        return False, "Connection refused - is FastAPI running?"
    except requests.exceptions.Timeout:
        return False, "Request timed out"
    except Exception as e:
        return False, f"Error: {str(e)}"

def main():
    print("=" * 70)
    print("Testing FastAPI Connection")
    print("=" * 70)
    print(f"FastAPI URL: {FASTAPI_URL}")
    print("=" * 70)
    print()
    
    results = {}
    
    # Test 1: Root endpoint
    print("1. Testing root endpoint (/)...")
    success, result = test_endpoint("root", "GET", f"{FASTAPI_URL}/")
    results["root"] = success
    if success:
        print("   ✓ OK")
    else:
        print(f"   ✗ FAILED: {result}")
    print()
    
    # Test 2: Health endpoint
    print("2. Testing health endpoint (/health)...")
    success, result = test_endpoint("health", "GET", f"{FASTAPI_URL}/health")
    results["health"] = success
    if success:
        print(f"   ✓ OK: {json.dumps(result, indent=2)}")
    else:
        print(f"   ✗ FAILED: {result}")
    print()
    
    # Test 3: Test endpoint
    print("3. Testing comprehensive test endpoint (/test)...")
    success, result = test_endpoint("test", "GET", f"{FASTAPI_URL}/test")
    results["test"] = success
    if success:
        print("   ✓ OK")
        if isinstance(result, dict):
            fastapi_status = result.get("fastapi_status", "unknown")
            weaviate_status = result.get("weaviate_connection", {}).get("status", "unknown")
            print(f"      FastAPI status: {fastapi_status}")
            print(f"      Weaviate connection: {weaviate_status}")
            if result.get("collections_available"):
                print(f"      Collections available: {len(result['collections_available'])}")
            if result.get("errors"):
                print(f"      Errors: {result['errors']}")
    else:
        print(f"   ✗ FAILED: {result}")
    print()
    
    # Test 4: GraphQL endpoint
    print("4. Testing GraphQL endpoint (/graphql)...")
    simple_query = """
    {
      Get {
        SongLyrics(limit: 1) {
          title
        }
      }
    }
    """
    success, result = test_endpoint(
        "graphql", 
        "POST", 
        f"{FASTAPI_URL}/graphql",
        json={"query": simple_query},
        headers={"Content-Type": "application/json"}
    )
    results["graphql"] = success
    if success:
        if isinstance(result, dict) and "errors" in result:
            print(f"   ✗ GraphQL errors: {result['errors']}")
            results["graphql"] = False
        else:
            print("   ✓ OK")
    else:
        print(f"   ✗ FAILED: {result}")
    print()
    
    # Test 5: Async endpoint
    print("5. Testing async endpoint (/graphql/async)...")
    payload = {
        "query_text": "love",
        "limit": 10,
        "alpha": 0.9
    }
    success, result = test_endpoint(
        "async",
        "POST",
        f"{FASTAPI_URL}/graphql/async",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    results["async"] = success
    if success:
        if isinstance(result, dict):
            successful_collections = result.get("successful_collections", 0)
            if successful_collections > 0:
                print(f"   ✓ OK ({successful_collections}/9 collections successful)")
            else:
                print(f"   ✗ No successful collections")
                results["async"] = False
        else:
            print("   ✓ OK")
    else:
        print(f"   ✗ FAILED: {result}")
    print()
    
    # Summary
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed
    
    for endpoint, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {endpoint:15} {status}")
    
    print()
    print(f"Total: {total} | Passed: {passed} | Failed: {failed}")
    print("=" * 70)
    
    if failed > 0:
        print("\n⚠️  Some tests failed. Please check:")
        print("   1. Is FastAPI running? (uvicorn fastapi_weaviate:app)")
        print("   2. Is Weaviate accessible? (check /test endpoint)")
        print("   3. Are the endpoints correct?")
        sys.exit(1)
    else:
        print("\n✓ All tests passed! Ready for Locust load testing.")
        sys.exit(0)

if __name__ == "__main__":
    main()

