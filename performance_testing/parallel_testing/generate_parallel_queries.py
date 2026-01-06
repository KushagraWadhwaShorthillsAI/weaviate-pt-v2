"""
PARALLEL QUERY GENERATOR - Generates queries for parallel collection testing.
Creates individual GraphQL queries (one per collection) to be executed in parallel.

This reuses embeddings from ../embeddings_cache.json (no API calls needed!)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import json
import argparse

# Collections for parallel testing (same as multi-collection)
COLLECTIONS = [
    'SongLyrics', 'SongLyrics_400k', 'SongLyrics_200k',
    'SongLyrics_50k', 'SongLyrics_30k', 'SongLyrics_20k', 
    'SongLyrics_15k', 'SongLyrics_12k', 'SongLyrics_10k'
]

# Test queries (40 total - same as generate_all_queries.py for consistency)
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
    # 10 additional queries for perfect 40-query split (10 per search type in mixed)
    "nature beauty mountains rivers", "faith hope spiritual journey", "young forever memories aging",
    "transformation change new beginnings", "rebel against system rules", "missing you come back",
    "adventure explore unknown world", "betrayal lies broken trust", "destiny fate written stars",
    "redemption forgiveness second chance"
]


def load_embeddings():
    """Load embeddings from parent directory cache"""
    cache_file = os.path.join(os.path.dirname(__file__), '..', 'embeddings_cache.json')
    
    if not os.path.exists(cache_file):
        print(f"❌ Error: {cache_file} not found!")
        print("   Run: python ../../utilities/generate_all_queries.py --type multi --search-types vector")
        print("   This will create the embeddings cache.")
        return None
    
    try:
        print(f"\n📦 Loading embeddings from {cache_file}...")
        with open(cache_file, 'r') as f:
            embeddings = json.load(f)
        
        # Verify all queries have embeddings
        missing = [q for q in SEARCH_QUERIES if q not in embeddings]
        if missing:
            print(f"❌ Missing embeddings for: {missing}")
            return None
        
        print(f"✅ Loaded {len(embeddings)} embeddings successfully!")
        return embeddings
    
    except Exception as e:
        print(f"❌ Error loading embeddings: {e}")
        return None


def generate_single_bm25_query(query_text, collection, limit):
    """Generate BM25 query for a SINGLE collection"""
    return f'''{{ Get {{
        {collection}(
          bm25: {{query: "{query_text}", properties: ["title", "lyrics"]}}
          limit: {limit}
        ) {{
          title tag artist year views features lyrics song_id language_cld3 language_ft language
          _additional {{ score }}
        }}
      }} }}'''


def generate_single_hybrid_query(query_text, query_vector, alpha, collection, limit):
    """Generate hybrid query for a SINGLE collection"""
    vector_str = json.dumps(query_vector)
    return f'''{{ Get {{
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
        }}
      }} }}'''


def generate_single_vector_query(query_vector, collection, limit):
    """Generate pure vector query for a SINGLE collection"""
    vector_str = json.dumps(query_vector)
    return f'''{{ Get {{
        {collection}(
          nearVector: {{
            vector: {vector_str}
          }}
          limit: {limit}
        ) {{
          title tag artist year views features lyrics song_id language_cld3 language_ft language
          _additional {{ distance }}
        }}
      }} }}'''


def generate_parallel_queries(search_type, limit, embeddings):
    """Generate parallel queries (9 separate queries per search term)"""
    
    all_query_sets = []
    
    print(f"\n🔨 Generating {search_type.upper()} queries (limit={limit})...")
    print(f"   Creating 40 query sets × 9 collections = 360 individual queries")
    
    for query_text in SEARCH_QUERIES:
        query_vector = embeddings.get(query_text)
        
        if not query_vector and search_type in ['vector', 'hybrid_01', 'hybrid_09']:
            print(f"⚠️  Skipping '{query_text}' - no embedding found")
            continue
        
        # Create 9 separate queries (one per collection)
        queries_for_parallel = []
        
        for collection in COLLECTIONS:
            if search_type == 'bm25':
                graphql = generate_single_bm25_query(query_text, collection, limit)
            
            elif search_type == 'vector':
                graphql = generate_single_vector_query(query_vector, collection, limit)
            
            elif search_type == 'hybrid_01':
                graphql = generate_single_hybrid_query(query_text, query_vector, 0.1, collection, limit)
            
            elif search_type == 'hybrid_09':
                graphql = generate_single_hybrid_query(query_text, query_vector, 0.9, collection, limit)
            
            else:
                print(f"❌ Unknown search type: {search_type}")
                return None
            
            queries_for_parallel.append({
                "collection": collection,
                "graphql": graphql.strip()
            })
        
        # Store this query set (9 queries to execute in parallel)
        all_query_sets.append({
            "query_text": query_text,
            "search_type": search_type,
            "limit": limit,
            "queries": queries_for_parallel  # List of 9 individual queries
        })
    
    print(f"✅ Generated {len(all_query_sets)} query sets")
    return all_query_sets


def generate_mixed_parallel_queries(limit, embeddings):
    """Generate mixed query sets (BM25, Hybrid 0.1, Hybrid 0.9, Vector)"""
    
    all_query_sets = []
    search_types = ['bm25', 'hybrid_01', 'hybrid_09', 'vector']
    
    print(f"\n🔨 Generating MIXED queries (limit={limit})...")
    print(f"   Creating 40 query sets × 9 collections = 360 individual queries")
    print(f"   Each set rotates through: {', '.join(search_types)} (10 queries per type)")
    
    for idx, query_text in enumerate(SEARCH_QUERIES):
        query_vector = embeddings.get(query_text)
        search_type = search_types[idx % 4]  # Rotate through types
        
        queries_for_parallel = []
        
        for collection in COLLECTIONS:
            if search_type == 'bm25':
                graphql = generate_single_bm25_query(query_text, collection, limit)
            elif search_type == 'vector':
                graphql = generate_single_vector_query(query_vector, collection, limit)
            elif search_type == 'hybrid_01':
                graphql = generate_single_hybrid_query(query_text, query_vector, 0.1, collection, limit)
            elif search_type == 'hybrid_09':
                graphql = generate_single_hybrid_query(query_text, query_vector, 0.9, collection, limit)
            
            queries_for_parallel.append({
                "collection": collection,
                "graphql": graphql.strip()
            })
        
        all_query_sets.append({
            "query_text": query_text,
            "search_type": search_type,
            "limit": limit,
            "queries": queries_for_parallel
        })
    
    print(f"✅ Generated {len(all_query_sets)} mixed query sets")
    return all_query_sets


def save_queries(queries, search_type, limit):
    """Save queries to JSON file"""
    output_dir = os.path.join(os.path.dirname(__file__), 'queries')
    os.makedirs(output_dir, exist_ok=True)
    
    filename = f"queries_{search_type}_{limit}.json"
    filepath = os.path.join(output_dir, filename)
    
    try:
        with open(filepath, 'w') as f:
            json.dump(queries, f, indent=2)
        print(f"💾 Saved: {filename}")
        return True
    except Exception as e:
        print(f"❌ Error saving {filename}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Generate parallel testing queries')
    parser.add_argument('--search-types', nargs='+', 
                        choices=['bm25', 'vector', 'hybrid_01', 'hybrid_09', 'mixed', 'all'],
                        default=['all'],
                        help='Search types to generate (default: all)')
    parser.add_argument('--limits', nargs='+', type=int,
                        choices=[10, 50, 100, 150, 200],
                        default=[10, 50, 100, 150, 200],
                        help='Result limits to generate (default: all)')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("🚀 PARALLEL QUERY GENERATOR")
    print("=" * 80)
    print(f"Collections: {len(COLLECTIONS)} (SongLyrics variants)")
    print(f"Search Queries: {len(SEARCH_QUERIES)}")
    print(f"Search Types: {args.search_types}")
    print(f"Limits: {args.limits}")
    print("=" * 80)
    
    # Load embeddings from cache
    embeddings = load_embeddings()
    if not embeddings:
        return
    
    # Determine which search types to generate
    if 'all' in args.search_types:
        search_types = ['bm25', 'vector', 'hybrid_01', 'hybrid_09', 'mixed']
    else:
        search_types = args.search_types
    
    # Generate queries for each combination
    total_files = 0
    for search_type in search_types:
        for limit in args.limits:
            if search_type == 'mixed':
                queries = generate_mixed_parallel_queries(limit, embeddings)
            else:
                queries = generate_parallel_queries(search_type, limit, embeddings)
            
            if queries:
                if save_queries(queries, search_type, limit):
                    total_files += 1
    
    print("\n" + "=" * 80)
    print(f"✅ SUCCESS! Generated {total_files} query files")
    print(f"📁 Location: parallel_testing/queries/")
    print(f"📊 Each file contains 40 query sets × 9 collections = 360 queries")
    print(f"📊 Mixed queries: Perfect 10 per search type (BM25, Hybrid 0.1, Hybrid 0.9, Vector)")
    print("=" * 80)
    print("\n🎯 Next steps:")
    print("   1. Run parallel tests: ./run_parallel_tests.sh")
    print("   2. Or run specific test:")
    print("      cd parallel_testing")
    print("      locust -f locustfile_vector.py --users 100 --spawn-rate 5 --run-time 5m --headless")
    print("=" * 80)


if __name__ == "__main__":
    main()

