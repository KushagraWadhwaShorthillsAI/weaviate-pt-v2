"""
Debug script to see raw node data from Weaviate API
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import requests
import json
import config

def debug_nodes():
    """Show raw node data"""
    
    print("="*70)
    print("DEBUG: Raw Weaviate Nodes API Response")
    print("="*70)
    print()
    
    headers = {"Content-Type": "application/json"}
    if config.WEAVIATE_API_KEY and config.WEAVIATE_API_KEY != "your-weaviate-api-key":
        headers["Authorization"] = f"Bearer {config.WEAVIATE_API_KEY}"
    
    try:
        response = requests.get(
            f"{config.WEAVIATE_URL}/v1/nodes",
            headers=headers,
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        print()
        
        if response.status_code == 200:
            data = response.json()
            
            # Pretty print the raw JSON
            print("Raw JSON Response:")
            print(json.dumps(data, indent=2))
            print()
            
            # Also check schema
            print("="*70)
            print("Checking if collections exist via schema API:")
            print("="*70)
            
            schema_response = requests.get(
                f"{config.WEAVIATE_URL}/v1/schema",
                headers=headers,
                timeout=30
            )
            
            if schema_response.status_code == 200:
                schema = schema_response.json()
                classes = schema.get('classes', [])
                print(f"\nFound {len(classes)} collection(s):")
                for cls in classes:
                    print(f"  • {cls['class']}")
                    print(f"    Sharding: {cls.get('shardingConfig', {}).get('desiredCount', 'N/A')} shards")
                    print(f"    Replication: {cls.get('replicationConfig', {}).get('factor', 'N/A')}")
            
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_nodes()

