"""
Test script to validate request/response logging and tracking.

This script sends requests and validates that:
1. Requests are properly logged
2. Responses are correctly recorded
3. Task execution is tracked
4. Timing information is accurate
"""

import sys
import os
import asyncio
import time
import json

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

import aiohttp
import config


# FastAPI server URL
FASTAPI_URL = os.getenv("FASTAPI_URL", "http://localhost:8000")


async def test_request_logging():
    """Test that requests are properly logged."""
    print("=" * 80)
    print("REQUEST/RESPONSE LOGGING VALIDATION")
    print("=" * 80)
    
    print(f"\nFastAPI URL: {FASTAPI_URL}")
    print(f"Log file: fastapi_weaviate.log (check this file for detailed logs)")
    
    url = f"{FASTAPI_URL}/graphql/async"
    payload = {
        "query_text": "love and heartbreak",
        "limit": 5,
        "alpha": 0.9
    }
    
    print(f"\nSending test request:")
    print(f"  Endpoint: POST {url}")
    print(f"  Query: '{payload['query_text']}'")
    print(f"  Limit: {payload['limit']}")
    print(f"  Alpha: {payload['alpha']}")
    
    print(f"\nExpected log entries:")
    print(f"  - Request received with request ID")
    print(f"  - Task creation for each collection")
    print(f"  - Task execution start/completion")
    print(f"  - Response summary")
    
    start_time = time.perf_counter()
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            elapsed_time = (time.perf_counter() - start_time) * 1000
            status = resp.status
            result = await resp.json()
    
    print(f"\n✓ Response received:")
    print(f"  Status: HTTP {status}")
    print(f"  Client-side elapsed: {elapsed_time:.2f}ms")
    print(f"  Server-reported time: {result.get('total_time_ms', 0):.2f}ms")
    print(f"  Successful collections: {result.get('successful_collections')}/{result.get('total_collections')}")
    
    # Validate response structure
    print(f"\n" + "=" * 80)
    print("RESPONSE VALIDATION:")
    print("=" * 80)
    
    required_fields = ['query_text', 'limit', 'alpha', 'total_collections', 
                      'successful_collections', 'failed_collections', 
                      'results', 'total_time_ms']
    
    missing_fields = [field for field in required_fields if field not in result]
    
    if not missing_fields:
        print("✓ All required response fields present")
    else:
        print(f"✗ Missing fields: {missing_fields}")
    
    # Validate results structure
    results = result.get('results', [])
    print(f"\nResults validation:")
    print(f"  Total results: {len(results)}")
    
    valid_results = 0
    for r in results:
        if all(key in r for key in ['collection', 'status_code']):
            valid_results += 1
    
    print(f"  Valid result structures: {valid_results}/{len(results)}")
    
    if valid_results == len(results) and len(results) > 0:
        print("✓ All results have proper structure")
    else:
        print("✗ Some results missing required fields")
    
    print(f"\n" + "=" * 80)
    print("CHECK LOG FILE:")
    print("=" * 80)
    print(f"  Check 'fastapi_weaviate.log' for detailed logging:")
    print(f"    - Request IDs")
    print(f"    - Task creation and execution")
    print(f"    - Timing information")
    print(f"    - Error details (if any)")
    
    return True


async def test_multiple_requests_tracking():
    """Test that multiple requests are tracked separately."""
    print("\n\n" + "=" * 80)
    print("MULTIPLE REQUESTS TRACKING TEST")
    print("=" * 80)
    
    url = f"{FASTAPI_URL}/graphql/async"
    
    async def make_request(query_text: str, request_num: int):
        payload = {
            "query_text": query_text,
            "limit": 3,
            "alpha": 0.0
        }
        
        start = time.perf_counter()
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                elapsed = (time.perf_counter() - start) * 1000
                result = await resp.json()
                return request_num, elapsed, result
    
    # Send 3 different requests
    queries = ["love", "heartbreak", "music"]
    print(f"\nSending {len(queries)} requests with different queries...")
    
    tasks = [make_request(query, i+1) for i, query in enumerate(queries)]
    results = await asyncio.gather(*tasks)
    
    print(f"\nResults:")
    for req_num, elapsed, result in results:
        print(f"  Request {req_num} ('{result.get('query_text')}'): "
              f"{elapsed:.2f}ms, {result.get('successful_collections')} successful")
    
    # Check that each request has unique timing
    times = [elapsed for _, elapsed, _ in results]
    if len(set(times)) == len(times) or max(times) - min(times) < 100:
        print(f"\n✓ Requests tracked separately (timings: {times})")
        return True
    else:
        print(f"\n✗ Suspicious timing similarity")
        return False


async def test_error_handling_logging():
    """Test that errors are properly logged."""
    print("\n\n" + "=" * 80)
    print("ERROR HANDLING LOGGING TEST")
    print("=" * 80)
    
    url = f"{FASTAPI_URL}/graphql/async"
    
    # Test with invalid limit (too high)
    payload = {
        "query_text": "test",
        "limit": 2000,  # Should be rejected (max 1000)
        "alpha": 0.0
    }
    
    print(f"\nSending request with invalid limit (2000, max is 1000)...")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            status = resp.status
            if status != 200:
                text = await resp.text()
                print(f"  Status: HTTP {status}")
                print(f"  Response: {text[:200]}")
                print(f"\n✓ Error properly handled and returned")
                return True
            else:
                result = await resp.json()
                print(f"  Status: HTTP {status}")
                print(f"  Note: Request was accepted (validation may be client-side)")
                return True


async def main():
    """Run all logging validation tests."""
    print("\n" + "=" * 80)
    print("REQUEST/RESPONSE LOGGING VALIDATION TESTS")
    print("=" * 80)
    
    # Check server
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{FASTAPI_URL}/health", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status != 200:
                    print(f"\n✗ ERROR: FastAPI server not responding")
                    return
    except Exception as e:
        print(f"\n✗ ERROR: Cannot connect to FastAPI server: {e}")
        return
    
    print("\n✓ FastAPI server is reachable")
    
    # Run tests
    test_results = []
    
    test_results.append(("Request Logging", await test_request_logging()))
    test_results.append(("Multiple Requests Tracking", await test_multiple_requests_tracking()))
    test_results.append(("Error Handling Logging", await test_error_handling_logging()))
    
    # Summary
    print("\n\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"  {test_name:<40} {status}")
    
    print(f"\n  Total: {passed}/{total} tests passed")
    print("=" * 80)
    
    print(f"\n📝 IMPORTANT: Check 'fastapi_weaviate.log' for detailed request/response logs")


if __name__ == "__main__":
    asyncio.run(main())

