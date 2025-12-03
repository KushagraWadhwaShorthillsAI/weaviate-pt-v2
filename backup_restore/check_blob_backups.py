"""
Check and analyze Weaviate backups in Azure Blob Storage.
Shows what's been backed up, file counts, sizes, and statistics.
"""


import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import sys
from collections import defaultdict
from datetime import datetime
from azure.storage.blob import BlobServiceClient


def format_size(bytes_size):
    """Format bytes to human-readable size"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"


def format_date(date_obj):
    """Format datetime to readable string"""
    if date_obj:
        return date_obj.strftime('%Y-%m-%d %H:%M:%S')
    return "N/A"


def check_backups(connection_string, container_name="weaviate-backups"):
    """
    Check all backup files in blob storage.
    
    Args:
        connection_string: Azure Blob Storage connection string
        container_name: Container name (default: weaviate-backups)
    """
    
    print("=" * 80)
    print("AZURE BLOB BACKUP CHECKER")
    print("=" * 80)
    print(f"\nContainer: {container_name}")
    print("\nConnecting to Azure Blob Storage...")
    
    try:
        # Connect to blob storage
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client(container_name)
        
        # Check if container exists
        try:
            container_client.get_container_properties()
            print(f"✅ Connected to container: {container_name}")
        except Exception as e:
            print(f"❌ Container '{container_name}' not found: {e}")
            return 1
        
        print("\n" + "-" * 80)
        print("Scanning backup files...")
        print("-" * 80)
        
        # List all blobs
        blobs = list(container_client.list_blobs())
        
        if not blobs:
            print("\n⚠️  No backup files found in container")
            return 0
        
        # Organize by collection and backup run
        collections = defaultdict(lambda: defaultdict(list))
        
        for blob in blobs:
            # Extract collection and backup run
            # Format: collection/backup_run_id/filename
            parts = blob.name.split('/')
            if len(parts) >= 2:
                collection = parts[0]
                backup_run = parts[1]
                collections[collection][backup_run].append(blob)
            else:
                # Old format without backup run
                collection = parts[0] if parts else 'root'
                collections[collection]['unknown'].append(blob)
        
        # Count total backup runs and files
        total_backup_runs = sum(len(runs) for runs in collections.values())
        
        # Display summary
        print(f"\n📊 Found {len(blobs)} backup files")
        print(f"   Collections: {len(collections)}")
        print(f"   Backup runs: {total_backup_runs}")
        
        print("\n" + "=" * 80)
        print("BACKUP SUMMARY BY COLLECTION")
        print("=" * 80)
        
        total_size = 0
        total_files = 0
        
        # Summary table
        print(f"\n{'Collection':<25} {'Runs':>6} {'Files':>8} {'Total Size':>15} {'Latest':<20}")
        print("-" * 80)
        
        for collection in sorted(collections.keys()):
            backup_runs = collections[collection]
            all_coll_blobs = [blob for run_blobs in backup_runs.values() for blob in run_blobs]
            coll_size = sum(blob.size for blob in all_coll_blobs)
            latest = max(all_coll_blobs, key=lambda b: b.last_modified).last_modified
            
            print(f"{collection:<25} {len(backup_runs):>6} {len(all_coll_blobs):>8} {format_size(coll_size):>15} {format_date(latest):<20}")
            
            total_size += coll_size
            total_files += len(all_coll_blobs)
        
        print("-" * 80)
        print(f"{'TOTAL':<25} {total_files:>8} {format_size(total_size):>15}")
        print("=" * 80)
        
        # Detailed breakdown (optional)
        print("\n📋 Detailed Breakdown:")
        print("=" * 80)
        
        for collection in sorted(collections.keys()):
            backup_runs = collections[collection]
            
            print(f"\n🔹 {collection}")
            print("-" * 80)
            print(f"   Backup runs: {len(backup_runs)}")
            
            # Show each backup run
            for run_id in sorted(backup_runs.keys(), reverse=True):
                run_blobs = backup_runs[run_id]
                run_size = sum(blob.size for blob in run_blobs)
                
                # Estimate objects
                total_objects = 0
                for blob in run_blobs:
                    if 'objs.json.gz' in blob.name:
                        try:
                            count_str = blob.name.split('_')[-1].replace('objs.json.gz', '')
                            total_objects += int(count_str)
                        except:
                            pass
                
                # Timestamps
                sorted_blobs = sorted(run_blobs, key=lambda b: b.last_modified)
                first_time = format_date(sorted_blobs[0].last_modified)
                last_time = format_date(sorted_blobs[-1].last_modified)
                
                print(f"\n   📁 {run_id}")
                print(f"      Files: {len(run_blobs)}, Size: {format_size(run_size)}, Objects: ~{total_objects:,}")
                print(f"      Created: {first_time}")
                
                # Show sample files for first backup run only
                if run_id == sorted(backup_runs.keys(), reverse=True)[0] and len(run_blobs) > 0:
                    print(f"      Sample files:")
                    for blob in run_blobs[:2]:
                        print(f"         • {blob.name.split('/')[-1]} ({format_size(blob.size)})")
                    if len(run_blobs) > 2:
                        print(f"         ... and {len(run_blobs) - 2} more")
        
        print("\n" + "=" * 80)
        print("✅ Backup check complete!")
        print("=" * 80)
        
        # Compression stats
        if total_files > 0:
            avg_compressed = total_size / total_files
            # Estimate uncompressed (assuming ~10% compression ratio)
            estimated_uncompressed = total_size / 0.1
            
            print(f"\n💾 Storage Statistics:")
            print(f"   Compressed size: {format_size(total_size)}")
            print(f"   Estimated uncompressed: {format_size(estimated_uncompressed)}")
            print(f"   Compression ratio: ~90%")
            print(f"   Savings: {format_size(estimated_uncompressed - total_size)}")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nPlease check:")
        print("  • Connection string is correct")
        print("  • Storage account is accessible")
        print("  • Container name is correct")
        return 1


def list_collections_only(connection_string, container_name="weaviate-backups"):
    """Quick list of collections with backup files"""
    
    try:
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client(container_name)
        
        # List unique collection names
        collections = set()
        for blob in container_client.list_blobs():
            collection = blob.name.split('/')[0] if '/' in blob.name else 'root'
            collections.add(collection)
        
        print("\n📁 Collections with backups:")
        for col in sorted(collections):
            print(f"   • {col}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


def main():
    """Main function"""
    
    import config
    
    print("╔" + "="*78 + "╗")
    print("║" + " "*22 + "AZURE BLOB BACKUP CHECKER" + " "*31 + "║")
    print("╚" + "="*78 + "╝")
    
    # Get connection string from config
    connection_string = config.AZURE_BLOB_CONNECTION_STRING
    
    if not connection_string or connection_string == "your-azure-blob-connection-string-here":
        print("\n❌ Azure Blob connection string not configured!")
        print("   Update AZURE_BLOB_CONNECTION_STRING in config.py")
        print("   Get from: Azure Portal → Storage Account → Access keys")
        return 1
    
    print("\n✓ Using connection string from config.py")
    
    # Container name from config
    container_name = getattr(config, 'AZURE_BLOB_CONTAINER_NAME', 'weaviate-backups')
    print(f"✓ Container: {container_name}")
    
    # Check type
    print("\n" + "=" * 80)
    print("Check Type:")
    print("  1. Full detailed report (default)")
    print("  2. Quick list of collections only")
    print("=" * 80)
    
    choice = input("\nChoice (1 or 2): ").strip()
    
    if choice == '2':
        return list_collections_only(connection_string, container_name)
    else:
        return check_backups(connection_string, container_name)


if __name__ == "__main__":
    sys.exit(main())

