"""
Check actual node shard distribution
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from weaviate_client import create_weaviate_client
from collections import defaultdict

def main():
    print("╔" + "="*78 + "╗")
    print("║" + " "*22 + "NODE SHARD DISTRIBUTION" + " "*33 + "║")
    print("╚" + "="*78 + "╝")
    print()
    
    client = create_weaviate_client()
    
    collections = [
        'SongLyrics', 'SongLyrics_400k', 'SongLyrics_200k',
        'SongLyrics_50k', 'SongLyrics_30k', 'SongLyrics_20k',
        'SongLyrics_15k', 'SongLyrics_12k', 'SongLyrics_10k'
    ]
    
    node_stats = defaultdict(lambda: {'shards': 0, 'objects': 0, 'collections': []})
    
    try:
        print("🔍 Checking all collections...")
        print()
        
        for collection_name in collections:
            if not client.collections.exists(collection_name):
                print(f"⚠️  {collection_name}: Does not exist")
                continue
            
            # Get sharding state
            sharding_state = client.cluster.query_sharding_state(collection=collection_name)
            
            for shard in sharding_state.shards:
                nodes = shard.replicas if hasattr(shard, 'replicas') else []
                obj_count = shard.object_count if hasattr(shard, 'object_count') else 0
                
                for node in nodes:
                    node_stats[node]['shards'] += 1
                    node_stats[node]['objects'] += obj_count
                    if collection_name not in node_stats[node]['collections']:
                        node_stats[node]['collections'].append(collection_name)
        
        print("=" * 78)
        print("🖥️  ACTUAL DISTRIBUTION")
        print("=" * 78)
        print()
        
        total_shards = sum(s['shards'] for s in node_stats.values())
        total_objects = sum(s['objects'] for s in node_stats.values())
        
        for node_name in sorted(node_stats.keys()):
            stats = node_stats[node_name]
            shard_pct = (stats['shards'] / total_shards * 100) if total_shards > 0 else 0
            obj_pct = (stats['objects'] / total_objects * 100) if total_objects > 0 else 0
            
            print(f"📍 {node_name}")
            print(f"   Shards:  {stats['shards']:3} ({shard_pct:5.1f}%)")
            if total_objects > 0:
                print(f"   Objects: {stats['objects']:,} ({obj_pct:5.1f}%)")
            else:
                print(f"   Objects: 0 (object count not available in API)")
            print(f"   Collections: {len(stats['collections'])}")
            print()
        
        print("-" * 78)
        print(f"TOTAL: {total_shards} shards | {total_objects:,} objects")
        print()
        
        # Balance check
        if len(node_stats) >= 2:
            shard_list = [s['shards'] for s in node_stats.values()]
            if max(shard_list) > 0:
                shard_imbalance = ((max(shard_list) - min(shard_list)) / max(shard_list) * 100)
                print(f"⚖️  Shard Balance: {shard_imbalance:.1f}% imbalance", end="")
                if shard_imbalance < 35:
                    print(" ✅")
                else:
                    print(" ⚠️")
        
        print()
        print("=" * 78)
        print(f"✅ {len(node_stats)} NODES UTILIZED")
        print("=" * 78)
        
    finally:
        client.close()

if __name__ == "__main__":
    main()
