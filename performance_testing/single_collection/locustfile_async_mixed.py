"""
Weaviate Async Client - Mixed Search on Single Collection
Uses Weaviate's native Python async client (NO GraphQL strings!)
Randomly selects between BM25, Hybrid (0.1), Hybrid (0.9), and Vector searches.

Usage:
    locust -f locustfile_async_mixed.py --users 100 --spawn-rate 5 --run-time 5m --headless
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

QUERIES_BY_TYPE = {}


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Load all query files when Locust starts"""
    global QUERIES_BY_TYPE
    
    print("=" * 70)
    print("Loading query files for Weaviate Async Client (Mixed Mode)...")
    print("=" * 70)
    
    query_files = {
        'bm25': 'queries/queries_bm25_200.json',
        'hybrid': 'queries/queries_hybrid_200.json',
        'vector': 'queries/queries_vector_200.json'
    }
    
    for search_type, filename in query_files.items():
        try:
            with open(filename, "r") as f:
                QUERIES_BY_TYPE[search_type] = json.load(f)
            print(f"✓ Loaded {search_type}: {len(QUERIES_BY_TYPE[search_type])} queries")
        except Exception as e:
            print(f"❌ Failed to load {filename}: {e}")
            QUERIES_BY_TYPE[search_type] = []
    
    print(f"  Mode: Weaviate Async Client (NO GraphQL!)")
    print(f"  Collection: {config.WEAVIATE_CLASS_NAME}")
    print(f"  Search types: BM25, Hybrid (0.1 & 0.9), Vector")
    print("=" * 70)


class WeaviateAsyncMixedUser(User):
    """User that performs mixed searches using Weaviate async client"""
    
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
    
    def extract_vector_from_query(self, query_data):
        """Extract vector from query data"""
        return query_data.get("vector")
    
    async def search_mixed_async(self, search_type, query_data):
        """Execute search based on type using Weaviate async client"""
        start_time = time.time()
        
        try:
            collection = self.client.collections.get(config.WEAVIATE_CLASS_NAME)
            query_text = query_data.get("query_text", "")
            limit = query_data["limit"]
            
            if search_type == "bm25":
                results = await collection.with_consistency_level(
                    consistency_level=ConsistencyLevel.ONE
                ).query.bm25(
                    query=query_text,
                    query_properties=["title", "lyrics"],
                    limit=limit,
                    return_properties=["title", "artist", "song_id"],
                    return_metadata=MetadataQuery(score=True)
                )
            elif search_type == "hybrid_01":
                query_vector = self.extract_vector_from_query(query_data)
                if not query_vector:
                    return {"success": False, "count": 0, "latency_ms": 0}
                results = await collection.with_consistency_level(
                    consistency_level=ConsistencyLevel.ONE
                ).query.hybrid(
                    query=query_text,
                    vector=query_vector,
                    alpha=0.1,
                    query_properties=["title", "lyrics"],
                    limit=limit,
                    return_properties=["title", "artist", "song_id"],
                    return_metadata=MetadataQuery(score=True)
                )
            elif search_type == "hybrid_09":
                query_vector = self.extract_vector_from_query(query_data)
                if not query_vector:
                    return {"success": False, "count": 0, "latency_ms": 0}
                results = await collection.with_consistency_level(
                    consistency_level=ConsistencyLevel.ONE
                ).query.hybrid(
                    query=query_text,
                    vector=query_vector,
                    alpha=0.9,
                    query_properties=["title", "lyrics"],
                    limit=limit,
                    return_properties=["title", "artist", "song_id"],
                    return_metadata=MetadataQuery(score=True)
                )
            elif search_type == "vector":
                query_vector = self.extract_vector_from_query(query_data)
                if not query_vector:
                    return {"success": False, "count": 0, "latency_ms": 0}
                results = await collection.with_consistency_level(
                    consistency_level=ConsistencyLevel.ONE
                ).query.near_vector(
                    near_vector=query_vector,
                    limit=limit,
                    return_properties=["title", "artist", "song_id"],
                    return_metadata=MetadataQuery(distance=True, certainty=True)
                )
            else:
                return {"success": False, "count": 0, "latency_ms": 0}
            
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
    def search_mixed(self):
        """Execute mixed search (randomly select type)"""
        if not QUERIES_BY_TYPE:
            return
        
        # Randomly select search type
        search_type = random.choice(['bm25', 'hybrid_01', 'hybrid_09', 'vector'])
        
        # Get appropriate query based on type
        if search_type == 'bm25':
            if not QUERIES_BY_TYPE.get('bm25'):
                return
            query_data = random.choice(QUERIES_BY_TYPE['bm25'])
        elif search_type in ['hybrid_01', 'hybrid_09']:
            if not QUERIES_BY_TYPE.get('hybrid'):
                return
            query_data = random.choice(QUERIES_BY_TYPE['hybrid'])
        else:  # vector
            if not QUERIES_BY_TYPE.get('vector'):
                return
            query_data = random.choice(QUERIES_BY_TYPE['vector'])
        
        request_start = time.time()
        
        try:
            loop = asyncio.get_event_loop()
            
            result = loop.run_until_complete(
                self.search_mixed_async(search_type, query_data)
            )
            
            total_time = int((time.time() - request_start) * 1000)
            
            if result["success"]:
                self.environment.events.request.fire(
                    request_type="WeaviateAsync",
                    name=f"Mixed_{search_type.upper()}_Single_Collection",
                    response_time=total_time,
                    response_length=result["count"],
                    exception=None,
                    context={}
                )
            else:
                self.environment.events.request.fire(
                    request_type="WeaviateAsync",
                    name=f"Mixed_{search_type.upper()}_Single_Collection",
                    response_time=total_time,
                    response_length=0,
                    exception=Exception(result.get("error", "Unknown error")),
                    context={}
                )
                
        except Exception as e:
            total_time = int((time.time() - request_start) * 1000)
            self.environment.events.request.fire(
                request_type="WeaviateAsync",
                name="Mixed_Single_Collection",
                response_time=total_time,
                response_length=0,
                exception=e,
                context={}
            )
