"""
Weaviate Async Client - Hybrid Search (alpha=0.1) on Single Collection
Uses Weaviate's native Python async client (NO GraphQL strings!)

Usage:
    locust -f locustfile_async_hybrid_01.py --users 100 --spawn-rate 5 --run-time 5m --headless
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import json
import random
import asyncio
import time
from locust import User, task, events
import weaviate
from weaviate.classes.query import MetadataQuery
from weaviate.classes.config import ConsistencyLevel
import config

QUERIES = []


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Load hybrid query file when Locust starts"""
    global QUERIES
    
    print("=" * 70)
    print("Loading hybrid query file for Weaviate Async Client...")
    print("=" * 70)
    
    try:
        with open("queries/queries_hybrid_200.json", "r") as f:
            QUERIES = json.load(f)
        print(f"✓ Loaded query file: {len(QUERIES)} queries")
        print(f"  Mode: Weaviate Async Client (NO GraphQL!)")
        print(f"  Collection: {config.WEAVIATE_CLASS_NAME}")
        print(f"  Hybrid alpha: 0.1 (90% BM25, 10% vector)")
        print("=" * 70)
    except Exception as e:
        print(f"❌ Failed to load queries_hybrid.json: {e}")
        print("=" * 70)


class WeaviateAsyncHybrid01User(User):
    """User that performs hybrid searches (alpha=0.1) using Weaviate async client"""
    
    abstract = False
    
    def __init__(self, environment):
        super().__init__(environment)
        self.client = None
    
    async def on_start_async(self):
        """Initialize Weaviate async client"""
        try:
            # Parse connection details from config
            url = config.WEAVIATE_URL
            url_without_protocol = url.replace("https://", "").replace("http://", "")
            
            if ":" in url_without_protocol:
                host, port_str = url_without_protocol.split(":", 1)
                port = int(port_str.split("/")[0])
            else:
                host = url_without_protocol.split("/")[0]
                port = 443 if url.startswith("https://") else 8080
            
            # Create async client
            self.client = weaviate.use_async_with_local(
                host=host,
                port=port,
                headers={"Authorization": f"Bearer {config.WEAVIATE_API_KEY}"} if config.WEAVIATE_API_KEY and config.WEAVIATE_API_KEY != "your-weaviate-api-key" else None
            )
            
            await self.client.connect()
            
        except Exception as e:
            print(f"Failed to connect to Weaviate: {e}")
            raise
    
    def on_start(self):
        """Sync wrapper for on_start"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.on_start_async())
    
    async def on_stop_async(self):
        """Close Weaviate client"""
        if self.client:
            await self.client.close()
    
    def on_stop(self):
        """Sync wrapper for on_stop"""
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.on_stop_async())
    
    async def search_hybrid_async(self, query_text, query_vector, limit):
        """Execute hybrid search using Weaviate async client"""
        start_time = time.time()
        
        try:
            collection = self.client.collections.get(config.WEAVIATE_CLASS_NAME)
            
            # Hybrid search with alpha=0.1 - NO GraphQL!
            results = await collection.with_consistency_level(
                consistency_level=ConsistencyLevel.ONE
            ).query.hybrid(
                query=query_text,
                vector=query_vector,
                alpha=0.1,  # 90% BM25, 10% vector
                query_properties=["title", "lyrics"],
                limit=limit,
                return_properties=["title", "artist", "song_id"],
                return_metadata=MetadataQuery(score=True)
            )
            
            elapsed = int((time.time() - start_time) * 1000)
            
            return {
                "success": True,
                "count": len(results.objects),
                "latency_ms": elapsed
            }
            
        except Exception as e:
            elapsed = int((time.time() - start_time) * 1000)
            return {
                "success": False,
                "count": 0,
                "latency_ms": elapsed,
                "error": str(e)
            }
    
    @task
    def search_hybrid(self):
        """Execute hybrid search"""
        if not QUERIES:
            return
        
        query_data = random.choice(QUERIES)
        query_text = query_data["query_text"]
        query_vector = query_data["vector"]
        limit = query_data["limit"]
        
        request_start = time.time()
        
        try:
            loop = asyncio.get_event_loop()
            
            result = loop.run_until_complete(
                self.search_hybrid_async(query_text, query_vector, limit)
            )
            
            total_time = int((time.time() - request_start) * 1000)
            
            if result["success"]:
                self.environment.events.request.fire(
                    request_type="WeaviateAsync",
                    name="Hybrid_01_Single_Collection",
                    response_time=total_time,
                    response_length=result["count"],
                    exception=None,
                    context={}
                )
            else:
                self.environment.events.request.fire(
                    request_type="WeaviateAsync",
                    name="Hybrid_01_Single_Collection",
                    response_time=total_time,
                    response_length=0,
                    exception=Exception(result.get("error", "Unknown error")),
                    context={}
                )
                
        except Exception as e:
            total_time = int((time.time() - request_start) * 1000)
            self.environment.events.request.fire(
                request_type="WeaviateAsync",
                name="Hybrid_01_Single_Collection",
                response_time=total_time,
                response_length=0,
                exception=e,
                context={}
            )
