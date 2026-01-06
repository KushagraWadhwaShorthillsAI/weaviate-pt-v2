"""
Delete Weaviate Collection - Safe deletion with confirmation.
Lists all collections and allows selection for deletion.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import requests
import config


def list_all_collections():
    """List all Weaviate collections"""
    headers = {"Content-Type": "application/json"}
    if config.WEAVIATE_API_KEY and config.WEAVIATE_API_KEY != "your-weaviate-api-key":
        headers["Authorization"] = f"Bearer {config.WEAVIATE_API_KEY}"
    
    try:
        response = requests.get(
            f"{config.WEAVIATE_URL}/v1/schema",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            schema = response.json()
            collections = [cls['class'] for cls in schema.get('classes', [])]
            return sorted(collections)
        else:
            print(f"❌ Failed to get schema: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error: {e}")
        return []


def count_objects(collection_name):
    """Count objects in a collection"""
    headers = {"Content-Type": "application/json"}
    if config.WEAVIATE_API_KEY and config.WEAVIATE_API_KEY != "your-weaviate-api-key":
        headers["Authorization"] = f"Bearer {config.WEAVIATE_API_KEY}"
    
    count_query = {
        "query": f"""
        {{
          Aggregate {{
            {collection_name} {{
              meta {{ count }}
            }}
          }}
        }}
        """
    }
    
    try:
        response = requests.post(
            f"{config.WEAVIATE_URL}/v1/graphql",
            headers=headers,
            json=count_query,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            count_data = result.get("data", {}).get("Aggregate", {}).get(collection_name, [])
            if count_data:
                return count_data[0].get("meta", {}).get("count", 0)
        return 0
    except:
        return 0


def delete_collection(collection_name):
    """Delete a Weaviate collection"""
    headers = {"Content-Type": "application/json"}
    if config.WEAVIATE_API_KEY and config.WEAVIATE_API_KEY != "your-weaviate-api-key":
        headers["Authorization"] = f"Bearer {config.WEAVIATE_API_KEY}"
    
    print(f"\n🗑️  Deleting collection '{collection_name}'...")
    
    response = requests.delete(
        f"{config.WEAVIATE_URL}/v1/schema/{collection_name}",
        headers=headers,
        timeout=30
    )
    
    if response.status_code == 200:
        print(f"✅ Collection '{collection_name}' deleted successfully")
        return True
    else:
        print(f"❌ Failed to delete: {response.status_code}")
        print(f"   Response: {response.text}")
        return False


def main():
    """Main function"""
    
    print("╔" + "="*68 + "╗")
    print("║" + " "*20 + "DELETE WEAVIATE COLLECTION" + " "*22 + "║")
    print("╚" + "="*68 + "╝")
    print()
    print(f"Weaviate URL: {config.WEAVIATE_URL}")
    print()
    
    # List all collections
    print("Fetching collections...")
    collections = list_all_collections()
    
    if not collections:
        print("❌ No collections found or couldn't connect to Weaviate")
        return 1
    
    print(f"\n✅ Found {len(collections)} collection(s):\n")
    
    # Show collections with object counts
    collection_info = []
    for i, col in enumerate(collections, 1):
        count = count_objects(col)
        collection_info.append((col, count))
        print(f"  {i:2}. {col:25} ({count:,} objects)")
    
    # Get user selection
    print("\n" + "="*70)
    print("⚠️  WARNING: This will PERMANENTLY delete the collection and all its data!")
    print("="*70)
    print("\nOptions:")
    print("  • Enter collection number to delete (e.g., '11')")
    print("  • Enter 'cancel' to abort")
    print()
    
    choice = input("Collection to delete: ").strip()
    
    if choice.lower() == 'cancel':
        print("✅ Operation cancelled")
        return 0
    
    try:
        index = int(choice)
        if 1 <= index <= len(collections):
            selected_collection, object_count = collection_info[index - 1]
        else:
            print("❌ Invalid collection number")
            return 1
    except:
        print("❌ Invalid input")
        return 1
    
    # Show what will be deleted
    print(f"\n⚠️  You are about to delete:")
    print(f"   Collection: {selected_collection}")
    print(f"   Objects: {object_count:,}")
    print()
    
    # Final confirmation
    print("To confirm, type the collection name exactly:")
    confirm = input(f"Type '{selected_collection}': ").strip()
    
    if confirm != selected_collection:
        print("❌ Name mismatch - deletion cancelled")
        return 0
    
    # Delete
    success = delete_collection(selected_collection)
    
    if success:
        print("\n" + "="*70)
        print("✅ DELETION SUCCESSFUL")
        print("="*70)
        print(f"\nCollection '{selected_collection}' has been deleted.")
        print(f"All {object_count:,} objects have been removed.")
        print("\n💡 If you have a backup, you can restore it with:")
        print("   cd backup_restore && python restore_from_blob.py")
        print("="*70)
        return 0
    else:
        print("\n❌ Deletion failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

