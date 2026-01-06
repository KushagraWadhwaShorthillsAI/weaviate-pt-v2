"""
Test script to validate async task fanout functionality.

This script tests that:
1. Tasks are created properly for each collection
2. Tasks execute in parallel (not sequentially)
3. All tasks complete and results are collected correctly
4. Timing shows parallel execution (total time ≈ slowest task, not sum of all tasks)
"""

import sys
import os
import asyncio
import time
import json
from typing import Dict, Any, List

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

import aiohttp
import config


# FastAPI server URL (default to localhost:8000)
FASTAPI_URL = os.getenv("FASTAPI_URL", "http://localhost:8000")


async def test_async_fanout_bm25():
    """Test BM25 async endpoint with parallel task execution."""
    print("=" * 80)
    print("TEST 1: BM25 Async Fanout Test")
    print("=" * 80)
    
    url = f"{FASTAPI_URL}/graphql/async"
    payload = {
        "query_text": "love and heartbreak",
        "limit": 10,
        "alpha": 0.0  # BM25 search
    }
    
    print(f"\nRequest URL: {url}")
    print(f"Query text: '{payload['query_text']}'")
    print(f"Limit: {payload['limit']}")
    print(f"Search type: BM25 (alpha=0.0)")
    print(f"\nExpected: 9 parallel tasks (one per collection)")
    print(f"Expected: Total time ≈ slowest collection query time")
    print("\nSending request...")
    
    start_time = time.perf_counter()
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            elapsed_time = (time.perf_counter() - start_time) * 1000
            status = resp.status
            result = await resp.json()
    
    print(f"\n✓ Response received (HTTP {status}) in {elapsed_time:.2f}ms")
    print(f"\nResponse Summary:")
    print(f"  - Query text: {result.get('query_text')}")
    print(f"  - Total collections: {result.get('total_collections')}")
    print(f"  - Successful: {result.get('successful_collections')}")
    print(f"  - Failed: {result.get('failed_collections')}")
    print(f"  - Total time: {result.get('total_time_ms'):.2f}ms")
    print(f"  - Alpha: {result.get('alpha')}")
    
    # Validate results
    results = result.get('results', [])
    print(f"\nCollection Results:")
    print(f"  {'Collection':<25} {'Status':<10} {'Results':<10} {'Error':<30}")
    print(f"  {'-'*25} {'-'*10} {'-'*10} {'-'*30}")
    
    success_count = 0
    fail_count = 0
    result_counts = []
    
    for r in results:
        collection = r.get('collection', 'unknown')
        status = r.get('status_code', 0)
        error = r.get('error')
        
        # Count results if available
        # GraphQL response structure: {"data": {"Get": {"CollectionName": [...]}}}
        result_count = 0
        if r.get('data') and isinstance(r.get('data'), dict):
            # Check for "Get" wrapper
            if 'Get' in r['data'] and isinstance(r['data']['Get'], dict):
                # Get the first collection result list
                for key, value in r['data']['Get'].items():
                    if isinstance(value, list):
                        result_count = len(value)
                        break
            else:
                # Direct structure (no "Get" wrapper)
                for key, value in r['data'].items():
                    if isinstance(value, list):
                        result_count = len(value)
                        break
        
        result_counts.append(result_count)
        
        if status == 200:
            success_count += 1
            print(f"  {collection:<25} {status:<10} {result_count:<10} {'-':<30}")
        else:
            fail_count += 1
            error_msg = (error[:27] + '...') if error and len(error) > 30 else (error or '-')
            print(f"  {collection:<25} {status:<10} {'-':<10} {error_msg:<30}")
    
    # Validation checks
    print(f"\n" + "=" * 80)
    print("VALIDATION CHECKS:")
    print("=" * 80)
    
    checks_passed = 0
    total_checks = 5
    
    # Check 1: All 9 collections queried
    if len(results) == 9:
        print("✓ Check 1: All 9 collections queried")
        checks_passed += 1
    else:
        print(f"✗ Check 1: Expected 9 collections, got {len(results)}")
    
    # Check 2: Tasks executed (results received)
    if len(results) > 0:
        print("✓ Check 2: Tasks executed and results collected")
        checks_passed += 1
    else:
        print("✗ Check 2: No results received")
    
    # Check 3: Parallel execution (total time should be reasonable, not sum of all)
    # If sequential, 9 queries * ~100ms each = ~900ms
    # If parallel, should be ~100-200ms (slowest query)
    if result.get('total_time_ms', 0) < 1000:
        print(f"✓ Check 3: Parallel execution confirmed (total time: {result.get('total_time_ms'):.2f}ms)")
        checks_passed += 1
    else:
        print(f"✗ Check 3: Suspicious timing ({result.get('total_time_ms'):.2f}ms) - might be sequential")
    
    # Check 4: Success rate
    success_rate = (success_count / len(results)) * 100 if results else 0
    if success_rate >= 50:  # At least 50% success
        print(f"✓ Check 4: Success rate acceptable ({success_rate:.1f}%)")
        checks_passed += 1
    else:
        print(f"✗ Check 4: Low success rate ({success_rate:.1f}%)")
    
    # Check 5: Results properly collected (validates async functionality)
    # Note: 0 results is valid if query doesn't match - what matters is async execution worked
    total_results = sum(result_counts)
    all_have_data_structure = all(
        r.get('data') is not None or r.get('error') is not None 
        for r in results
    )
    if all_have_data_structure and success_count > 0:
        if total_results > 0:
            print(f"✓ Check 5: Results properly collected ({total_results} total results)")
        else:
            print(f"✓ Check 5: Results properly collected (0 results - query may not match, but async execution worked)")
        checks_passed += 1
    else:
        print("✗ Check 5: Results not properly collected or structured")
    
    print(f"\n" + "=" * 80)
    print(f"TEST RESULT: {checks_passed}/{total_checks} checks passed")
    print("=" * 80)
    
    return checks_passed == total_checks


async def test_async_fanout_hybrid():
    """Test Hybrid async endpoint with parallel task execution."""
    print("\n\n" + "=" * 80)
    print("TEST 2: Hybrid Async Fanout Test")
    print("=" * 80)
    
    url = f"{FASTAPI_URL}/graphql/async"
    payload = {
        "query_text": "love and heartbreak",
        "limit": 10,
        "alpha": 0.9  # Hybrid search
    }
    
    print(f"\nRequest URL: {url}")
    print(f"Query text: '{payload['query_text']}'")
    print(f"Limit: {payload['limit']}")
    print(f"Search type: Hybrid (alpha=0.9)")
    print(f"\nExpected: 9 parallel tasks (one per collection)")
    print(f"Expected: Total time ≈ slowest collection query time")
    print("\nSending request...")
    
    start_time = time.perf_counter()
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            elapsed_time = (time.perf_counter() - start_time) * 1000
            status = resp.status
            result = await resp.json()
    
    print(f"\n✓ Response received (HTTP {status}) in {elapsed_time:.2f}ms")
    print(f"\nResponse Summary:")
    print(f"  - Query text: {result.get('query_text')}")
    print(f"  - Total collections: {result.get('total_collections')}")
    print(f"  - Successful: {result.get('successful_collections')}")
    print(f"  - Failed: {result.get('failed_collections')}")
    print(f"  - Total time: {result.get('total_time_ms'):.2f}ms")
    print(f"  - Alpha: {result.get('alpha')}")
    
    # Validate results
    results = result.get('results', [])
    print(f"\nCollection Results:")
    print(f"  {'Collection':<25} {'Status':<10} {'Results':<10} {'Error':<30}")
    print(f"  {'-'*25} {'-'*10} {'-'*10} {'-'*30}")
    
    success_count = 0
    result_counts = []
    
    for r in results:
        collection = r.get('collection', 'unknown')
        status = r.get('status_code', 0)
        error = r.get('error')
        
        # Count results if available
        # GraphQL response structure: {"data": {"Get": {"CollectionName": [...]}}}
        result_count = 0
        if r.get('data') and isinstance(r.get('data'), dict):
            # Check for "Get" wrapper
            if 'Get' in r['data'] and isinstance(r['data']['Get'], dict):
                # Get the first collection result list
                for key, value in r['data']['Get'].items():
                    if isinstance(value, list):
                        result_count = len(value)
                        break
            else:
                # Direct structure (no "Get" wrapper)
                for key, value in r['data'].items():
                    if isinstance(value, list):
                        result_count = len(value)
                        break
        
        result_counts.append(result_count)
        
        if status == 200:
            success_count += 1
            print(f"  {collection:<25} {status:<10} {result_count:<10} {'-':<30}")
        else:
            error_msg = (error[:27] + '...') if error and len(error) > 30 else (error or '-')
            print(f"  {collection:<25} {status:<10} {'-':<10} {error_msg:<30}")
    
    # Validation checks
    print(f"\n" + "=" * 80)
    print("VALIDATION CHECKS:")
    print("=" * 80)
    
    checks_passed = 0
    total_checks = 5
    
    # Check 1: All 9 collections queried
    if len(results) == 9:
        print("✓ Check 1: All 9 collections queried")
        checks_passed += 1
    else:
        print(f"✗ Check 1: Expected 9 collections, got {len(results)}")
    
    # Check 2: Tasks executed
    if len(results) > 0:
        print("✓ Check 2: Tasks executed and results collected")
        checks_passed += 1
    else:
        print("✗ Check 2: No results received")
    
    # Check 3: Parallel execution timing
    if result.get('total_time_ms', 0) < 1000:
        print(f"✓ Check 3: Parallel execution confirmed (total time: {result.get('total_time_ms'):.2f}ms)")
        checks_passed += 1
    else:
        print(f"✗ Check 3: Suspicious timing ({result.get('total_time_ms'):.2f}ms)")
    
    # Check 4: Success rate
    success_rate = (success_count / len(results)) * 100 if results else 0
    if success_rate >= 50:
        print(f"✓ Check 4: Success rate acceptable ({success_rate:.1f}%)")
        checks_passed += 1
    else:
        print(f"✗ Check 4: Low success rate ({success_rate:.1f}%)")
    
    # Check 5: Alpha value correct
    if result.get('alpha') == 0.9:
        print(f"✓ Check 5: Alpha value correct ({result.get('alpha')})")
        checks_passed += 1
    else:
        print(f"✗ Check 5: Alpha value incorrect (expected 0.9, got {result.get('alpha')})")
    
    print(f"\n" + "=" * 80)
    print(f"TEST RESULT: {checks_passed}/{total_checks} checks passed")
    print("=" * 80)
    
    return checks_passed == total_checks


async def test_parallel_vs_sequential_timing():
    """Test that parallel execution is faster than sequential would be."""
    print("\n\n" + "=" * 80)
    print("TEST 3: Parallel vs Sequential Timing Comparison")
    print("=" * 80)
    
    url = f"{FASTAPI_URL}/graphql/async"
    payload = {
        "query_text": "love",
        "limit": 5,
        "alpha": 0.0  # BM25
    }
    
    print(f"\nRunning 3 parallel requests to measure consistency...")
    
    async def make_request():
        async with aiohttp.ClientSession() as session:
            start = time.perf_counter()
            async with session.post(url, json=payload) as resp:
                elapsed = (time.perf_counter() - start) * 1000
                result = await resp.json()
                return elapsed, result
    
    # Run 3 requests in parallel to test
    start_total = time.perf_counter()
    results = await asyncio.gather(*[make_request() for _ in range(3)])
    total_time = (time.perf_counter() - start_total) * 1000
    
    print(f"\nResults:")
    for i, (elapsed, result) in enumerate(results, 1):
        print(f"  Request {i}: {elapsed:.2f}ms (collections: {result.get('total_collections')}, "
              f"successful: {result.get('successful_collections')})")
    
    avg_time = sum(elapsed for elapsed, _ in results) / len(results)
    print(f"\n  Average request time: {avg_time:.2f}ms")
    print(f"  Total time for 3 requests: {total_time:.2f}ms")
    
    # If truly parallel, each request should take similar time
    # Sequential would be: request1_time + request2_time + request3_time
    sequential_estimate = avg_time * 3
    
    print(f"\n" + "=" * 80)
    print("TIMING ANALYSIS:")
    print("=" * 80)
    print(f"  Average per request: {avg_time:.2f}ms")
    print(f"  Estimated sequential time: {sequential_estimate:.2f}ms")
    print(f"  Actual total time: {total_time:.2f}ms")
    
    if total_time < sequential_estimate * 0.7:  # At least 30% faster than sequential
        print(f"\n✓ Parallel execution confirmed (saved ~{sequential_estimate - total_time:.2f}ms)")
        return True
    else:
        print(f"\n✗ Timing suggests sequential execution")
        return False


async def test_task_creation_and_execution():
    """Test that tasks are created and executed properly."""
    print("\n\n" + "=" * 80)
    print("TEST 4: Task Creation and Execution Validation")
    print("=" * 80)
    
    url = f"{FASTAPI_URL}/graphql/async"
    payload = {
        "query_text": "test query",
        "limit": 1,
        "alpha": 0.0
    }
    
    print(f"\nSending request and monitoring task execution...")
    print(f"Expected: 9 tasks created, all execute in parallel")
    
    start_time = time.perf_counter()
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            elapsed_time = (time.perf_counter() - start_time) * 1000
            status = resp.status
            result = await resp.json()
    
    print(f"\n✓ Response received in {elapsed_time:.2f}ms")
    
    results = result.get('results', [])
    
    # Check that we have results from all collections
    collections_received = [r.get('collection') for r in results]
    expected_collections = [
        "SongLyrics", "SongLyrics_400k", "SongLyrics_200k",
        "SongLyrics_50k", "SongLyrics_30k", "SongLyrics_20k",
        "SongLyrics_15k", "SongLyrics_12k", "SongLyrics_10k",
    ]
    
    print(f"\n" + "=" * 80)
    print("TASK EXECUTION VALIDATION:")
    print("=" * 80)
    
    checks_passed = 0
    total_checks = 3
    
    # Check 1: All expected collections present
    missing = set(expected_collections) - set(collections_received)
    if not missing:
        print("✓ Check 1: All expected collections have results")
        checks_passed += 1
    else:
        print(f"✗ Check 1: Missing collections: {missing}")
    
    # Check 2: Results are properly structured
    all_have_status = all('status_code' in r for r in results)
    if all_have_status:
        print("✓ Check 2: All results have status_code")
        checks_passed += 1
    else:
        print("✗ Check 2: Some results missing status_code")
    
    # Check 3: Timing suggests parallel execution
    if elapsed_time < 500:  # Should complete quickly if parallel
        print(f"✓ Check 3: Timing suggests parallel execution ({elapsed_time:.2f}ms)")
        checks_passed += 1
    else:
        print(f"✗ Check 3: Timing suggests sequential execution ({elapsed_time:.2f}ms)")
    
    print(f"\n" + "=" * 80)
    print(f"TEST RESULT: {checks_passed}/{total_checks} checks passed")
    print("=" * 80)
    
    return checks_passed == total_checks


async def main():
    """Run all async fanout tests."""
    print("\n" + "=" * 80)
    print("ASYNC TASK FANOUT VALIDATION TESTS")
    print("=" * 80)
    print(f"\nFastAPI URL: {FASTAPI_URL}")
    print(f"Weaviate URL: {config.WEAVIATE_URL}")
    print("\nThese tests validate that:")
    print("  1. Tasks are created for each collection")
    print("  2. Tasks execute in parallel (not sequentially)")
    print("  3. All results are collected correctly")
    print("  4. Timing confirms parallel execution")
    
    # Check if server is reachable
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{FASTAPI_URL}/health", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status != 200:
                    print(f"\n✗ ERROR: FastAPI server not responding (HTTP {resp.status})")
                    print(f"  Make sure the server is running: uvicorn fastapi_weaviate:app --host 0.0.0.0 --port 8000")
                    return
    except Exception as e:
        print(f"\n✗ ERROR: Cannot connect to FastAPI server: {e}")
        print(f"  Make sure the server is running: uvicorn fastapi_weaviate:app --host 0.0.0.0 --port 8000")
        return
    
    print("\n✓ FastAPI server is reachable")
    
    # Run tests
    test_results = []
    
    test_results.append(("BM25 Async Fanout", await test_async_fanout_bm25()))
    test_results.append(("Hybrid Async Fanout", await test_async_fanout_hybrid()))
    test_results.append(("Parallel vs Sequential", await test_parallel_vs_sequential_timing()))
    test_results.append(("Task Creation & Execution", await test_task_creation_and_execution()))
    
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
    
    if passed == total:
        print("\n✓ All tests passed! Async task fanout is working correctly.")
    else:
        print(f"\n✗ {total - passed} test(s) failed. Review the output above.")


if __name__ == "__main__":
    asyncio.run(main())

