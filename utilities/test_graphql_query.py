"""
Test GraphQL query to diagnose collection copying issues.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import requests
import json
import config


def test_query():
    """Test if we can fetch objects from SongLyrics"""
    
    headers = {"Content-Type": "application/json"}
    if config.WEAVIATE_API_KEY and config.WEAVIATE_API_KEY != "your-weaviate-api-key":
        headers["Authorization"] = f"Bearer {config.WEAVIATE_API_KEY}"
    
    print("=" * 70)
    print("GRAPHQL QUERY TEST")
    print("=" * 70)
    print(f"\nWeaviate URL: {config.WEAVIATE_URL}")
    print(f"Source Collection: {config.WEAVIATE_CLASS_NAME}")
    
    # Test 1: Simple count query
    print("\n1️⃣  Testing count query...")
    count_query = {
        "query": f"""
        {{
          Aggregate {{
            {config.WEAVIATE_CLASS_NAME} {{
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
        json=count_query,
        timeout=30
    )
    
    if response.status_code == 200:
        result = response.json()
        if "errors" in result:
            print(f"   ❌ GraphQL errors: {result['errors']}")
        else:
            count_data = result.get("data", {}).get("Aggregate", {}).get(config.WEAVIATE_CLASS_NAME, [])
            if count_data:
                count = count_data[0].get("meta", {}).get("count", 0)
                print(f"   ✅ Collection has {count:,} objects")
            else:
                print(f"   ❌ Could not get count")
                print(f"   Response: {json.dumps(result, indent=2)}")
    else:
        print(f"   ❌ Request failed: {response.status_code}")
        print(f"   Response: {response.text}")
    
    # Test 2: Fetch first 5 objects
    print("\n2️⃣  Testing fetch query (first 5 objects)...")
    fetch_query = {
        "query": f"""
        {{
          Get {{
            {config.WEAVIATE_CLASS_NAME}(limit: 5) {{
              title
              artist
              song_id
              _additional {{
                id
              }}
            }}
          }}
        }}
        """
    }
    
    response = requests.post(
        f"{config.WEAVIATE_URL}/v1/graphql",
        headers=headers,
        json=fetch_query,
        timeout=30
    )
    
    if response.status_code == 200:
        result = response.json()
        if "errors" in result:
            print(f"   ❌ GraphQL errors:")
            for error in result['errors']:
                print(f"      • {error.get('message', error)}")
        else:
            objects = result.get("data", {}).get("Get", {}).get(config.WEAVIATE_CLASS_NAME, [])
            if objects:
                print(f"   ✅ Successfully fetched {len(objects)} objects")
                print(f"\n   Sample object:")
                if len(objects) > 0:
                    obj = objects[0]
                    print(f"      Title: {obj.get('title', 'N/A')}")
                    print(f"      Artist: {obj.get('artist', 'N/A')}")
                    print(f"      Song ID: {obj.get('song_id', 'N/A')}")
                    print(f"      UUID: {obj.get('_additional', {}).get('id', 'N/A')}")
            else:
                print(f"   ⚠️  Query succeeded but returned 0 objects")
                print(f"   Full response:")
                print(json.dumps(result, indent=2))
    else:
        print(f"   ❌ Request failed: {response.status_code}")
        print(f"   Response: {response.text}")
    
    # Test 3: Fetch with vector
    print("\n3️⃣  Testing fetch query WITH vector...")
    vector_query = {
        "query": f"""
        {{
          Get {{
            {config.WEAVIATE_CLASS_NAME}(limit: 2) {{
              title
              _additional {{
                id
                vector
              }}
            }}
          }}
        }}
        """
    }
    
    response = requests.post(
        f"{config.WEAVIATE_URL}/v1/graphql",
        headers=headers,
        json=vector_query,
        timeout=30
    )
    
    if response.status_code == 200:
        result = response.json()
        if "errors" in result:
            print(f"   ❌ GraphQL errors:")
            for error in result['errors']:
                print(f"      • {error.get('message', error)}")
        else:
            objects = result.get("data", {}).get("Get", {}).get(config.WEAVIATE_CLASS_NAME, [])
            if objects and len(objects) > 0:
                obj = objects[0]
                vector = obj.get('_additional', {}).get('vector', [])
                print(f"   ✅ Successfully fetched object with vector")
                print(f"      Title: {obj.get('title', 'N/A')}")
                print(f"      Vector length: {len(vector)} dimensions")
                if len(vector) > 0:
                    print(f"      Vector sample: [{vector[0]:.4f}, {vector[1]:.4f}, ...]")
                else:
                    print(f"      ⚠️  Vector is empty!")
            else:
                print(f"   ⚠️  No objects returned")
                print(f"   Response: {json.dumps(result, indent=2)}")
    else:
        print(f"   ❌ Request failed: {response.status_code}")
    
    print("\n" + "=" * 70)
    print("DIAGNOSIS:")
    print("=" * 70)
    print("If all tests pass, copying should work.")
    print("If any test fails, check the error messages above.")
    print("=" * 70)


if __name__ == "__main__":
    test_query()

