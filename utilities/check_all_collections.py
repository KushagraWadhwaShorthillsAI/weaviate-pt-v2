import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

"""
Check object counts in all collections.
Shows if data was successfully copied.
"""

import requests
import config


def count_objects_in_collection(collection_name):
    """Count objects in a specific collection"""
    try:
        headers = {"Content-Type": "application/json"}
        if config.WEAVIATE_API_KEY and config.WEAVIATE_API_KEY != "your-weaviate-api-key":
            headers["Authorization"] = f"Bearer {config.WEAVIATE_API_KEY}"
        
        query = {
            "query": f"""
            {{
              Aggregate {{
                {collection_name} {{
                  meta {{
                    count
                  }}
                }}
              }}
            }}
            """
        }
        
        response = requests.post(
            f"{config.WEAVIATE_URL}/v1/graphql",
            headers=headers,
            json=query,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            aggregate_data = result.get("data", {}).get("Aggregate", {}).get(collection_name, [])
            if aggregate_data and len(aggregate_data) > 0:
                count = aggregate_data[0].get("meta", {}).get("count", 0)
                return count
            return 0
        else:
            return None
            
    except Exception as e:
        return None


def main():
    """Check all collections"""
    collections_to_check = [
        ("SongLyrics", 1000000, "Source collection"),
        ("SongLyrics_400k", 400000, "4 lakh"),
        ("SongLyrics_200k", 200000, "2 lakh"),
        ("SongLyrics_50k", 50000, "50k"),
        ("SongLyrics_30k", 30000, "30k"),
        ("SongLyrics_20k", 20000, "20k"),
        ("SongLyrics_15k", 15000, "15k"),
        ("SongLyrics_12k", 12000, "12k"),
        ("SongLyrics_10k", 10000, "10k"),
    ]
    
    print("=" * 80)
    print("COLLECTION STATUS CHECK")
    print("=" * 80)
    print(f"\nWeaviate URL: {config.WEAVIATE_URL}")
    print("\nChecking all collections...")
    print("-" * 80)
    
    results = []
    
    for name, expected, description in collections_to_check:
        count = count_objects_in_collection(name)
        results.append((name, expected, count, description))
    
    # Display results
    print(f"\n{'Collection':<25} {'Expected':>12} {'Actual':>12} {'Status':>10} {'Description':<20}")
    print("-" * 80)
    
    total_expected = 0
    total_actual = 0
    
    for name, expected, actual, description in results:
        total_expected += expected
        
        if actual is None:
            status = "❌ ERROR"
            actual_str = "N/A"
        elif actual == 0:
            status = "⚠️  EMPTY"
            actual_str = "0"
            total_actual += actual
        elif actual == expected:
            status = "✅ OK"
            actual_str = f"{actual:,}"
            total_actual += actual
        elif actual < expected:
            status = "⚠️  PARTIAL"
            actual_str = f"{actual:,}"
            total_actual += actual
        else:
            status = "⚠️  MORE"
            actual_str = f"{actual:,}"
            total_actual += actual
        
        print(f"{name:<25} {expected:>12,} {actual_str:>12} {status:>10} {description:<20}")
    
    print("-" * 80)
    print(f"{'TOTAL':<25} {total_expected:>12,} {total_actual:>12,}")
    print("=" * 80)
    
    # Summary
    empty_collections = [name for name, _, actual, _ in results if actual == 0]
    error_collections = [name for name, _, actual, _ in results if actual is None]
    partial_collections = [name for name, exp, actual, _ in results if actual is not None and 0 < actual < exp]
    complete_collections = [name for name, exp, actual, _ in results if actual == exp]
    
    print("\n📊 Summary:")
    print(f"   ✅ Complete: {len(complete_collections)} collections")
    print(f"   ⚠️  Empty: {len(empty_collections)} collections")
    print(f"   ⚠️  Partial: {len(partial_collections)} collections")
    print(f"   ❌ Error: {len(error_collections)} collections")
    
    if empty_collections:
        print(f"\n⚠️  Empty collections (need data copy):")
        for name in empty_collections:
            print(f"      • {name}")
        print(f"\n   To copy data, run:")
        print(f"      python create_multiple_collections.py")
        print(f"      (Type 'no' when asked about deleting existing collections)")
    
    if error_collections:
        print(f"\n❌ Collections with errors:")
        for name in error_collections:
            print(f"      • {name} (doesn't exist - needs schema creation)")
    
    if partial_collections:
        print(f"\n⚠️  Partially filled collections:")
        for name in partial_collections:
            expected = next(exp for n, exp, _, _ in results if n == name)
            actual = next(act for n, _, act, _ in results if n == name)
            remaining = expected - actual if actual else expected
            print(f"      • {name}: {actual:,}/{expected:,} ({remaining:,} remaining)")
    
    if len(complete_collections) == len(collections_to_check):
        print(f"\n🎉 All collections are complete!")
        return 0
    else:
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

