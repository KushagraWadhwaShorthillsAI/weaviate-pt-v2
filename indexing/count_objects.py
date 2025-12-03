"""
Simple script to count the number of objects in a Weaviate collection.
Shows total count and breakdown by collection.
"""


import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import sys
import requests
import config


def count_objects_rest_api(collection_name=None):
    """
    Count objects using REST API (GraphQL).
    Works with HTTP-only Weaviate servers.
    
    Args:
        collection_name: Collection to count (defaults to config.WEAVIATE_CLASS_NAME)
    
    Returns:
        Number of objects, or None on error
    """
    if collection_name is None:
        collection_name = config.WEAVIATE_CLASS_NAME
    
    try:
        # Prepare headers
        headers = {"Content-Type": "application/json"}
        if config.WEAVIATE_API_KEY and config.WEAVIATE_API_KEY != "your-weaviate-api-key":
            headers["Authorization"] = f"Bearer {config.WEAVIATE_API_KEY}"
        
        # GraphQL query to count objects
        graphql_query = {
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
        
        # Send request
        response = requests.post(
            f"{config.WEAVIATE_URL}/v1/graphql",
            headers=headers,
            json=graphql_query,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # Extract count from response
            aggregate_data = result.get("data", {}).get("Aggregate", {}).get(collection_name, [])
            if aggregate_data and len(aggregate_data) > 0:
                count = aggregate_data[0].get("meta", {}).get("count", 0)
                return count
            else:
                return 0
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error counting objects: {e}")
        return None


def get_all_collections():
    """Get list of all collections in Weaviate"""
    try:
        headers = {"Content-Type": "application/json"}
        if config.WEAVIATE_API_KEY and config.WEAVIATE_API_KEY != "your-weaviate-api-key":
            headers["Authorization"] = f"Bearer {config.WEAVIATE_API_KEY}"
        
        response = requests.get(
            f"{config.WEAVIATE_URL}/v1/schema",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            schema = response.json()
            classes = schema.get("classes", [])
            return [cls.get("class") for cls in classes]
        else:
            return []
            
    except Exception as e:
        print(f"Error getting collections: {e}")
        return []


def main():
    """Main function to count and display objects"""
    print("=" * 70)
    print("WEAVIATE OBJECT COUNTER")
    print("=" * 70)
    print(f"\nWeaviate URL: {config.WEAVIATE_URL}")
    print(f"Collection: {config.WEAVIATE_CLASS_NAME}")
    print("\nCounting objects...")
    print("-" * 70)
    
    # Count objects in configured collection
    count = count_objects_rest_api(config.WEAVIATE_CLASS_NAME)
    
    if count is not None:
        print(f"\n✅ Count successful!")
        print(f"\n📊 Collection: {config.WEAVIATE_CLASS_NAME}")
        print(f"   Total objects: {count:,}")
        
        if count == 0:
            print("\n   ⚠️  Collection is empty")
            print("      Run 'python process_lyrics.py' to index data")
        elif count < 1000:
            print(f"\n   Status: Test data ({count} objects)")
        elif count < config.MAX_ROWS_TO_PROCESS:
            percentage = (count / config.MAX_ROWS_TO_PROCESS) * 100
            print(f"\n   Status: {percentage:.2f}% of target ({config.MAX_ROWS_TO_PROCESS:,})")
            print(f"   Remaining: {config.MAX_ROWS_TO_PROCESS - count:,} objects")
        else:
            print(f"\n   Status: Target reached!")
        
        # Show all collections
        print("\n" + "-" * 70)
        print("All collections in Weaviate:")
        collections = get_all_collections()
        if collections:
            for coll in collections:
                coll_count = count_objects_rest_api(coll)
                print(f"  • {coll}: {coll_count:,} objects" if coll_count is not None else f"  • {coll}")
        else:
            print("  No collections found")
        
        print("=" * 70)
        return 0
    else:
        print("\n❌ Failed to count objects")
        print("   Please check:")
        print("   1. Weaviate is running")
        print("   2. WEAVIATE_URL is correct in config.py")
        print("   3. Collection exists (run create_weaviate_schema.py)")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())

