"""
Restore Weaviate collections from Azure Blob Storage.
Updated to Weaviate v4 client - Based on proven working approach.

Usage:
    # Restore all files
    python restore_v4.py
    
    # Restore specific file range (e.g., files 1-10)
    python restore_v4.py --start 1 --end 10
    
    # Restore from file 5 onwards
    python restore_v4.py --start 5
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import gc
import time
import argparse
from typing import List, Dict
from azure.storage.blob import BlobServiceClient
from tqdm import tqdm

import config
from weaviate_client import create_weaviate_client


def list_backup_files(blob_service_client, container_name, collection_name, backup_prefix=None):
    """List all backup files for a collection"""
    try:
        container_client = blob_service_client.get_container_client(container_name)
        
        # List all blobs for this collection
        prefix = f"{collection_name}/"
        if backup_prefix:
            prefix = f"{collection_name}/{backup_prefix}/"
        
        blobs = container_client.list_blobs(name_starts_with=prefix)
        blob_list = sorted([blob.name for blob in blobs if blob.name.endswith('.json')])
        
        return blob_list
        
    except Exception as e:
        print(f"Error listing blobs: {e}")
        return []


def read_blob_content(blob_service_client, container_name, blob_name):
    """Download and parse blob content"""
    try:
        container_client = blob_service_client.get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_name)
        
        blob_data = blob_client.download_blob().readall()
        json_data = json.loads(blob_data)
        
        return json_data
        
    except Exception as e:
        print(f"Error reading blob {blob_name}: {e}")
        return None


def restore_batch_v4(collection_name, json_data):
    """
    Restore batch using REST API (faster and more reliable).
    
    Args:
        collection_name: Target collection
        json_data: List of objects to restore
    
    Returns:
        (success_count, error_count)
    """
    try:
        import requests
        
        headers = {"Content-Type": "application/json"}
        if config.WEAVIATE_API_KEY and config.WEAVIATE_API_KEY != "your-weaviate-api-key":
            headers["Authorization"] = f"Bearer {config.WEAVIATE_API_KEY}"
        
        # Prepare batch payload for REST API
        batch_objects = []
        for data in json_data:
            # Extract vector
            vector = data.get('_additional', {}).get('vector')
            
            # Extract properties (exclude _additional)
            properties = {k: v for k, v in data.items() if k != '_additional'}
            
            batch_objects.append({
                "class": collection_name,
                "properties": properties,
                "vector": vector
            })
        
        # Send batch insert via REST API
        response = requests.post(
            f"{config.WEAVIATE_URL}/v1/batch/objects",
            headers=headers,
            json={"objects": batch_objects},
            timeout=300  # 5 minutes for large batches
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # Count successes
            success_count = 0
            error_count = 0
            
            for item in result:
                if item.get("result", {}).get("errors"):
                    error_count += 1
                else:
                    success_count += 1
            
            # If no explicit counts, assume all succeeded
            if success_count == 0 and error_count == 0:
                success_count = len(batch_objects)
            
            return success_count, error_count
        else:
            print(f"Batch insert failed: {response.status_code}")
            return 0, len(json_data)
        
    except Exception as e:
        print(f"Batch restore error: {e}")
        return 0, len(json_data)


def restore_collection(client, collection_name, azure_connection_string, container_name, 
                      backup_prefix=None, start_index=None, end_index=None):
    """
    Restore a collection from Azure Blob Storage.
    
    Args:
        client: Weaviate client
        collection_name: Collection to restore
        azure_connection_string: Azure connection
        container_name: Azure container
        backup_prefix: Specific backup to restore (None to list and choose)
        start_index: Start file index (1-based, None for all)
        end_index: End file index (inclusive, None for all)
    """
    print(f"\n{'='*70}")
    print(f"Restoring: {collection_name}")
    print(f"{'='*70}\n")
    
    # Connect to Azure
    blob_service_client = BlobServiceClient.from_connection_string(azure_connection_string)
    
    # If no prefix specified, let user choose
    if not backup_prefix:
        # List available backups
        container_client = blob_service_client.get_container_client(container_name)
        blobs = container_client.list_blobs(name_starts_with=f"{collection_name}/backup_")
        
        backup_runs = set()
        for blob in blobs:
            parts = blob.name.split('/')
            if len(parts) >= 2 and parts[1].startswith('backup_'):
                backup_runs.add(parts[1])
        
        if not backup_runs:
            print(f"❌ No backups found for {collection_name}")
            blob_service_client.close()
            return 0
        
        backup_runs = sorted(list(backup_runs), reverse=True)
        
        print("Available backups:")
        for i, run in enumerate(backup_runs, 1):
            print(f"  {i}. {run}")
        
        choice = int(input(f"\nSelect backup (1-{len(backup_runs)}): "))
        backup_prefix = backup_runs[choice - 1]
    
    print(f"\n✅ Using backup: {backup_prefix}\n")
    
    # Get list of backup files
    blob_files = list_backup_files(blob_service_client, container_name, collection_name, backup_prefix)
    
    if not blob_files:
        print(f"❌ No backup files found")
        blob_service_client.close()
        return 0
    
    print(f"Found {len(blob_files)} backup files")
    
    # Apply file range filter if specified
    if start_index is not None or end_index is not None:
        start_idx = (start_index - 1) if start_index else 0  # Convert to 0-based
        end_idx = end_index if end_index else len(blob_files)
        
        blob_files = blob_files[start_idx:end_idx]
        
        print(f"   Filtered to files {start_idx + 1} to {end_idx} ({len(blob_files)} files)")
    
    print()
    
    # Restore each file
    total_restored = 0
    total_errors = 0
    
    try:
        with tqdm(total=len(blob_files), desc=f"Restoring {collection_name}", unit="file") as pbar:
            for blob_name in blob_files:
                try:
                    # Download blob
                    json_data = read_blob_content(blob_service_client, container_name, blob_name)
                    
                    if not json_data:
                        pbar.update(1)
                        continue
                    
                    # Restore batch using REST API (faster!)
                    success, errors = restore_batch_v4(collection_name, json_data)
                    
                    total_restored += success
                    total_errors += errors
                    
                    # Clear references immediately
                    json_data = None
                    
                    pbar.update(1)
                    
                    # Aggressive memory cleanup
                    collected = gc.collect()
                    
                    # Extra GC every 5 files
                    if pbar.n % 5 == 0:
                        for _ in range(2):
                            collected += gc.collect()
                        print(f"\n   🧹 Memory cleaned: freed {collected} objects, restored: {total_restored:,}")
                    
                    time.sleep(0.5)
                    
                except Exception as e:
                    print(f"\n❌ Error processing {blob_name}: {e}")
                    pbar.update(1)
                    continue
    
    finally:
        # Always close blob client
        blob_service_client.close()
        
        # Final aggressive garbage collection
        print(f"\n🧹 Final cleanup...")
        for i in range(3):
            collected = gc.collect()
            if collected > 0:
                print(f"   GC pass {i+1}: freed {collected} objects")
    
    print(f"\n{'='*70}")
    print(f"✅ Restore complete: {collection_name}")
    print(f"   Objects restored: {total_restored:,}")
    print(f"   Errors: {total_errors}")
    print(f"{'='*70}\n")
    
    return total_restored


def main():
    """Main restore function"""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Restore Weaviate collections from Azure Blob')
    parser.add_argument('--start', type=int, help='Start file index (1-based)', default=None)
    parser.add_argument('--end', type=int, help='End file index (inclusive)', default=None)
    args = parser.parse_args()
    
    print("╔" + "="*68 + "╗")
    print("║" + " "*18 + "RESTORE FROM AZURE BLOB" + " "*27 + "║")
    print("╚" + "="*68 + "╝")
    print()
    
    if args.start or args.end:
        print(f"📋 File range filter:")
        print(f"   Start: {args.start if args.start else 'beginning'}")
        print(f"   End: {args.end if args.end else 'end'}")
        print()
    
    # Check Azure configuration
    if not config.AZURE_BLOB_CONNECTION_STRING or \
       config.AZURE_BLOB_CONNECTION_STRING == "your-azure-blob-connection-string-here":
        print("❌ Azure Blob connection string not configured!")
        return 1
    
    print(f"Weaviate URL: {config.WEAVIATE_URL}")
    print(f"Azure Container: {config.AZURE_BLOB_CONTAINER_NAME}")
    print()
    
    # Get available backed up collections
    blob_service_client = BlobServiceClient.from_connection_string(config.AZURE_BLOB_CONNECTION_STRING)
    container_client = blob_service_client.get_container_client(config.AZURE_BLOB_CONTAINER_NAME)
    
    blobs = container_client.list_blobs()
    collections_with_backups = set()
    for blob in blobs:
        collection_name = blob.name.split('/')[0]
        collections_with_backups.add(collection_name)
    
    blob_service_client.close()
    
    if not collections_with_backups:
        print("❌ No backups found in Azure Blob Storage")
        return 1
    
    print("Collections with backups:")
    collections_list = sorted(list(collections_with_backups))
    for i, col in enumerate(collections_list, 1):
        print(f"  {i}. {col}")
    
    print()
    choice = int(input(f"Select collection to restore (1-{len(collections_list)}): "))
    collection_to_restore = collections_list[choice - 1]
    
    print(f"\n✅ Selected: {collection_to_restore}")
    
    # Confirm
    confirm = input(f"\nThis will restore {collection_to_restore}. Proceed? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("❌ Restore cancelled")
        return 0
    
    # Connect to Weaviate
    print("\nConnecting to Weaviate...")
    client = create_weaviate_client()
    print("✅ Connected")
    
    # Check if collection exists
    if not client.collections.exists(collection_to_restore):
        print(f"\n⚠️  Collection '{collection_to_restore}' doesn't exist")
        print(f"   Creating schema first...")
        
        # Import create_all_schemas to create schema
        from create_all_schemas import create_schema
        result = create_schema(collection_to_restore)
        
        if result != 'created' and result != 'exists':
            print(f"❌ Failed to create schema")
            client.close()
            return 1
    
    # Restore
    try:
        restored = restore_collection(
            client,
            collection_to_restore,
            config.AZURE_BLOB_CONNECTION_STRING,
            config.AZURE_BLOB_CONTAINER_NAME,
            start_index=args.start,
            end_index=args.end
        )
        
        print(f"\n🎉 Restore successful!")
        print(f"   Collection: {collection_to_restore}")
        print(f"   Objects: {restored:,}")
        
    finally:
        client.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

