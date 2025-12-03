"""
Create multiple collections by copying data from source collection.
Batch script to create all required collections with specified object counts.
Includes aggressive memory management for large-scale operations.
"""


import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import sys
import time
import gc
from copy_collection import CollectionCopier
import config


# Configuration for all collections to create
COLLECTIONS_CONFIG = [
    # Collection 1: Already done manually (1 million objects)
    # {"name": "SongLyrics", "count": 1000000, "skip": True},
    
    # Collection 2: 4 lakh (400,000)
    {"name": "SongLyrics_400k", "count": 400000, "description": "400k objects"},
    
    # Collection 3: 2 lakh (200,000)
    {"name": "SongLyrics_200k", "count": 200000, "description": "200k objects"},
    
    # Collections 4-9: 10k-50k objects each
    {"name": "SongLyrics_50k", "count": 50000, "description": "50k objects"},
    {"name": "SongLyrics_30k", "count": 30000, "description": "30k objects"},
    {"name": "SongLyrics_20k", "count": 20000, "description": "20k objects"},
    {"name": "SongLyrics_15k", "count": 15000, "description": "15k objects"},
    {"name": "SongLyrics_12k", "count": 12000, "description": "12k objects"},
    {"name": "SongLyrics_10k", "count": 10000, "description": "10k objects"},
]


def create_all_collections(source_collection: str = None, batch_size: int = None):
    """
    Create all configured collections by copying from source.
    
    Args:
        source_collection: Source collection name (defaults to config.WEAVIATE_CLASS_NAME)
        batch_size: Batch size for copying (defaults to config.COPY_BATCH_SIZE)
    """
    if batch_size is None:
        batch_size = getattr(config, 'COPY_BATCH_SIZE', 100)
    if source_collection is None:
        source_collection = config.WEAVIATE_CLASS_NAME
    
    print("=" * 70)
    print("BATCH COLLECTION CREATOR")
    print("=" * 70)
    print(f"\nSource Collection: {source_collection}")
    print(f"Target Collections: {len(COLLECTIONS_CONFIG)}")
    print(f"\nCollections to create:")
    print("-" * 70)
    
    total_objects = 0
    for i, coll in enumerate(COLLECTIONS_CONFIG, 1):
        if coll.get('skip'):
            print(f"{i}. {coll['name']:25} {coll['count']:>10,} objects [SKIP]")
        else:
            print(f"{i}. {coll['name']:25} {coll['count']:>10,} objects")
            total_objects += coll['count']
    
    print("-" * 70)
    print(f"Total objects to copy: {total_objects:,}")
    print("=" * 70)
    
    # Confirm
    confirm = input("\nProceed with creating all collections? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("❌ Operation cancelled")
        return 1
    
    # Process each collection
    results = []
    
    for i, coll_config in enumerate(COLLECTIONS_CONFIG, 1):
        if coll_config.get('skip'):
            print(f"\n⏭️  Skipping {coll_config['name']}")
            continue
        
        print("\n" + "=" * 70)
        print(f"Collection {i}/{len(COLLECTIONS_CONFIG)}: {coll_config['name']}")
        print("=" * 70)
        
        # Create copier
        copier = CollectionCopier(source_collection, coll_config['name'])
        
        # Create schema
        print(f"\n📝 Creating schema for {coll_config['name']}...")
        if not copier.create_target_schema():
            print(f"❌ Failed to create schema for {coll_config['name']}")
            results.append((coll_config['name'], 0, coll_config['count']))
            continue
        
        # Copy objects
        print(f"\n📦 Copying {coll_config['count']:,} objects...")
        success, errors = copier.copy_objects(coll_config['count'], batch_size=batch_size)
        
        results.append((coll_config['name'], success, errors))
        
        print(f"\n✓ {coll_config['name']}: {success:,} copied, {errors:,} errors")
        
        # Aggressive garbage collection between collections
        print("\n🧹 Cleaning up memory...")
        collected = gc.collect()
        print(f"   GC: {collected} objects freed")
        
        # Small delay between collections
        if i < len(COLLECTIONS_CONFIG):
            print("⏸️  Waiting 3 seconds before next collection...")
            time.sleep(3)
    
    # Final summary
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    
    for name, success, errors in results:
        status = "✅" if errors == 0 else "⚠️"
        print(f"{status} {name:25} {success:>10,} copied, {errors:>6,} errors")
    
    total_copied = sum(s for _, s, _ in results)
    total_errors = sum(e for _, _, e in results)
    
    print("-" * 70)
    print(f"   {'Total':25} {total_copied:>10,} copied, {total_errors:>6,} errors")
    print("=" * 70)
    
    if total_errors == 0:
        print("\n🎉 All collections created successfully!")
    else:
        print(f"\n⚠️  Completed with {total_errors:,} total errors")
    
    # Final cleanup
    print("\n🧹 Final memory cleanup...")
    for i in range(3):
        collected = gc.collect()
        print(f"   Final GC pass {i+1}: {collected} objects collected")
    
    print("\n✅ All resources cleaned up")
    
    return 0


if __name__ == "__main__":
    sys.exit(create_all_collections())

