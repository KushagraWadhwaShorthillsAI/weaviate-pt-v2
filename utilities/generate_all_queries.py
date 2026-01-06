"""
UNIFIED QUERY GENERATOR - Generates ALL query types for performance testing.
Handles: BM25, Hybrid (0.1 & 0.9), Vector, and Mixed queries.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import argparse
from openai_client import create_sync_openai_client
import config

# Collections for multi-collection testing
MULTI_COLLECTIONS = [
    'SongLyrics', 'SongLyrics_400k', 'SongLyrics_200k',
    'SongLyrics_50k', 'SongLyrics_30k', 'SongLyrics_20k', 'SongLyrics_15k', 'SongLyrics_12k', 'SongLyrics_10k'
]

# Test queries (40 total for perfect 4-way split in mixed queries)
SEARCH_QUERIES = [
    "love and heartbreak", "summer party vibes", "feeling alone tonight",
    "dance all night long", "broken dreams and hope", "city lights at midnight",
    "memories of yesterday", "living life to fullest", "chasing dreams forever",
    "never give up fighting", "friendship and loyalty", "money power respect",
    "family comes first always", "trust nobody believe yourself", "hustle grind every day",
    "success and motivation", "romantic love story", "pain and suffering",
    "celebration and joy", "freedom and liberty", "hope for better tomorrow",
    "struggle and perseverance", "peace and tranquility", "anger and revenge",
    "happiness and laughter", "sadness and tears", "victory and triumph",
    "loss and defeat", "passion and desire", "fear and courage",
    "nature beauty mountains rivers", "faith hope spiritual journey", "young forever memories aging",
    "transformation change new beginnings", "rebel against system rules", "missing you come back",
    "adventure explore unknown world", "betrayal lies broken trust", "destiny fate written stars",
    "redemption forgiveness second chance"
]


def get_embeddings(cache_file=None):
    """Get embeddings for all queries (cached for reuse)"""
    
    # Default cache file location: performance_testing/embeddings_cache.json
    if cache_file is None:
        cache_file = os.path.join(os.path.dirname(__file__), '..', 'performance_testing', 'embeddings_cache.json')
    
    # Try to load from cache first
    if os.path.exists(cache_file):
        try:
            print(f"\n📦 Loading cached embeddings from {cache_file}...")
            with open(cache_file, 'r') as f:
                embeddings = json.load(f)
            
            # Verify all queries have embeddings
            if all(query in embeddings for query in SEARCH_QUERIES):
                print(f"✅ Loaded {len(embeddings)} cached embeddings")
                return embeddings
            else:
                print("⚠️  Cache incomplete, regenerating...")
        except Exception as e:
            print(f"⚠️  Cache error: {e}, regenerating...")
    
    # Generate fresh embeddings
    print("\n🔄 Generating embeddings for 40 queries (this takes ~40 seconds)...")
    print("   These will be cached for future use!")
    
    client, model = create_sync_openai_client()
    embeddings = {}
    
    for i, query in enumerate(SEARCH_QUERIES, 1):
        print(f"  [{i}/40] {query}...", end=' ', flush=True)
        try:
            response = client.embeddings.create(model=model, input=query)
            embeddings[query] = response.data[0].embedding
            print("✓")
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    # Save to cache
    try:
        with open(cache_file, 'w') as f:
            json.dump(embeddings, f)
        print(f"\n💾 Saved embeddings to {cache_file} (will reuse next time)")
    except Exception as e:
        print(f"\n⚠️  Could not save cache: {e}")
    
    return embeddings


def generate_bm25_query(query_text, collections, limit):
    """Generate BM25 query for multiple collections"""
    collection_queries = []
    for collection in collections:
        collection_queries.append(f'''
        {collection}(
          bm25: {{query: "{query_text}", properties: ["title", "lyrics"]}}
          limit: {limit}
        ) {{
          title tag artist year views features lyrics song_id language_cld3 language_ft language
          _additional {{ score }}
        }}''')
    
    all_collections = "\n        ".join(collection_queries)
    return f"{{ Get {{ {all_collections} }} }}"


def generate_hybrid_query(query_text, query_vector, alpha, collections, limit):
    """Generate Hybrid query"""
    vector_str = json.dumps(query_vector)
    collection_queries = []
    
    for collection in collections:
        collection_queries.append(f'''
        {collection}(
          hybrid: {{
            query: "{query_text}"
            alpha: {alpha}
            vector: {vector_str}
            properties: ["title", "lyrics"]
          }}
          limit: {limit}
        ) {{
          title tag artist year views features lyrics song_id language_cld3 language_ft language
          _additional {{ score }}
        }}''')
    
    all_collections = "\n        ".join(collection_queries)
    return f"{{ Get {{ {all_collections} }} }}"


def generate_vector_query(query_vector, collections, limit):
    """Generate pure vector query"""
    vector_str = json.dumps(query_vector)
    collection_queries = []
    
    for collection in collections:
        collection_queries.append(f'''
        {collection}(
          nearVector: {{vector: {vector_str}}}
          limit: {limit}
        ) {{
          title tag artist year views features lyrics song_id language_cld3 language_ft language
          _additional {{ distance certainty }}
        }}''')
    
    all_collections = "\n        ".join(collection_queries)
    return f"{{ Get {{ {all_collections} }} }}"


def generate_all_query_files(test_type, limit, collections, output_dir='.'):
    """Generate query files for specific test type and limit"""
    
    print(f"\n{'='*70}")
    print(f"Generating {test_type.upper()} queries (limit={limit})")
    print(f"{'='*70}")
    
    # Get embeddings if needed
    embeddings = None
    if test_type in ['hybrid_01', 'hybrid_09', 'vector', 'mixed']:
        embeddings = get_embeddings()
        if not embeddings:
            return False
    
    queries = []
    
    if test_type == 'bm25':
        for query_text in SEARCH_QUERIES:
            queries.append({
                "query_text": query_text,
                "search_type": "bm25",
                "limit": limit,
                "graphql": generate_bm25_query(query_text, collections, limit)
            })
    
    elif test_type == 'hybrid_01':
        for query_text in SEARCH_QUERIES:
            queries.append({
                "query_text": query_text,
                "search_type": "hybrid_01",
                "limit": limit,
                "graphql": generate_hybrid_query(query_text, embeddings[query_text], 0.1, collections, limit)
            })
    
    elif test_type == 'hybrid_09':
        for query_text in SEARCH_QUERIES:
            queries.append({
                "query_text": query_text,
                "search_type": "hybrid_09",
                "limit": limit,
                "graphql": generate_hybrid_query(query_text, embeddings[query_text], 0.9, collections, limit)
            })
    
    elif test_type == 'vector':
        for query_text in SEARCH_QUERIES:
            queries.append({
                "query_text": query_text,
                "search_type": "vector",
                "limit": limit,
                "graphql": generate_vector_query(embeddings[query_text], collections, limit)
            })
    
    elif test_type == 'mixed':
        # Mix of all four types (BM25, Hybrid 0.1, Hybrid 0.9, Vector)
        # With 40 queries: 10 of each type for perfect balance
        for i, query_text in enumerate(SEARCH_QUERIES):
            if i % 4 == 0:
                search_type = 'bm25'
                graphql = generate_bm25_query(query_text, collections, limit)
            elif i % 4 == 1:
                search_type = 'hybrid_01'
                graphql = generate_hybrid_query(query_text, embeddings[query_text], 0.1, collections, limit)
            elif i % 4 == 2:
                search_type = 'hybrid_09'
                graphql = generate_hybrid_query(query_text, embeddings[query_text], 0.9, collections, limit)
            else:  # i % 4 == 3
                search_type = 'vector'
                graphql = generate_vector_query(embeddings[query_text], collections, limit)
            
            queries.append({
                "query_text": query_text,
                "search_type": search_type,
                "limit": limit,
                "graphql": graphql
            })
    
    # Save to queries subfolder
    queries_dir = os.path.join(output_dir, 'queries')
    os.makedirs(queries_dir, exist_ok=True)
    
    filename = os.path.join(queries_dir, f"queries_{test_type}_{limit}.json")
    with open(filename, 'w') as f:
        json.dump(queries, f, indent=2)
    
    print(f"✅ Created: {filename} ({len(queries)} queries)")
    return True


def main():
    parser = argparse.ArgumentParser(description='Generate ALL PT queries')
    parser.add_argument('--type', choices=['multi', 'single'], default='multi',
                        help='multi=9 collections, single=SongLyrics only')
    parser.add_argument('--limits', nargs='+', type=int, default=[10, 50, 100, 150, 200],
                        help='Result limits to generate (default: 10 50 100 150 200)')
    parser.add_argument('--search-types', nargs='+', 
                        choices=['bm25', 'hybrid_01', 'hybrid_09', 'vector', 'mixed'],
                        default=['bm25', 'hybrid_01', 'hybrid_09', 'vector', 'mixed'],
                        help='Search types to generate')
    
    args = parser.parse_args()
    
    # Set collections based on type
    # Output directories are relative to performance_testing/
    perf_testing_dir = os.path.join(os.path.dirname(__file__), '..', 'performance_testing')
    if args.type == 'multi':
        collections = MULTI_COLLECTIONS
        output_dir = os.path.join(perf_testing_dir, 'multi_collection')
        print("Generating queries for MULTI-COLLECTION (9 collections)")
    else:
        collections = [config.WEAVIATE_CLASS_NAME]
        output_dir = os.path.join(perf_testing_dir, 'single_collection')
        print(f"Generating queries for SINGLE-COLLECTION ({config.WEAVIATE_CLASS_NAME})")
    
    print(f"Limits: {args.limits}")
    print(f"Search types: {args.search_types}")
    print("="*70)
    
    # Generate for each combination
    total = len(args.limits) * len(args.search_types)
    completed = 0
    
    for search_type in args.search_types:
        for limit in args.limits:
            if generate_all_query_files(search_type, limit, collections, output_dir):
                completed += 1
            else:
                print(f"❌ Failed to generate {search_type} limit {limit}")
    
    print("\n" + "="*70)
    print(f"✅ Generated {completed}/{total} query files")
    print("="*70)
    
    return 0 if completed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

