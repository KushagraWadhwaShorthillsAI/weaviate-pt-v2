"""
Run all async functionality tests.

This script runs all test suites to validate:
1. Async task fanout functionality
2. Request/response logging
3. Error handling
"""

import sys
import os
import asyncio

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from test_async_fanout import main as test_fanout
from test_request_response_logging import main as test_logging


async def main():
    """Run all test suites."""
    print("\n" + "=" * 80)
    print("COMPREHENSIVE ASYNC FUNCTIONALITY TEST SUITE")
    print("=" * 80)
    
    print("\nThis will run:")
    print("  1. Async Task Fanout Tests")
    print("  2. Request/Response Logging Tests")
    
    input("\nPress Enter to start tests...")
    
    # Run test suites
    print("\n" + "=" * 80)
    print("TEST SUITE 1: Async Task Fanout")
    print("=" * 80)
    await test_fanout()
    
    print("\n\n" + "=" * 80)
    print("TEST SUITE 2: Request/Response Logging")
    print("=" * 80)
    await test_logging()
    
    print("\n\n" + "=" * 80)
    print("ALL TESTS COMPLETE")
    print("=" * 80)
    print("\nCheck the logs:")
    print("  - Console output: Test results above")
    print("  - Log file: fastapi_weaviate.log (detailed request/response logs)")


if __name__ == "__main__":
    asyncio.run(main())

