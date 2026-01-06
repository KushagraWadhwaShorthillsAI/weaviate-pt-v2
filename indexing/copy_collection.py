"""
Copy objects from one Weaviate collection to another without re-embedding.
Reuses existing vectors to save embedding costs.
Configurable number of objects to copy.
Includes aggressive garbage collection for large-scale copying.
"""


import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import requests
import logging
import sys
import gc
from typing import List, Dict, Any, Optional
from tqdm import tqdm
import time

import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CollectionCopier:
    """Copy objects between Weaviate collections"""
    
    def __init__(self, source_collection: str, target_collection: str):
        self.source_collection = source_collection
        self.target_collection = target_collection
        self.base_url = config.WEAVIATE_URL
        self.headers = {"Content-Type": "application/json"}
        
        if config.WEAVIATE_API_KEY and config.WEAVIATE_API_KEY != "your-weaviate-api-key":
            self.headers["Authorization"] = f"Bearer {config.WEAVIATE_API_KEY}"
    
    def create_target_schema(self):
        """Create target collection with same schema as source"""
        logger.info(f"Creating schema for collection: {self.target_collection}")
        
        try:
            # Get source schema
            response = requests.get(
                f"{self.base_url}/v1/schema/{self.source_collection}",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to get source schema: {response.status_code}")
                return False
            
            source_schema = response.json()
            
            # Create new schema with target collection name
            target_schema = source_schema.copy()
            target_schema['class'] = self.target_collection
            target_schema['description'] = f"Copy of {self.source_collection}"
            
            # Check if target already exists
            check_response = requests.get(
                f"{self.base_url}/v1/schema/{self.target_collection}",
                headers=self.headers,
                timeout=10
            )
            
            if check_response.status_code == 200:
                logger.warning(f"Collection {self.target_collection} already exists!")
                user_input = input(f"Delete and recreate {self.target_collection}? (yes/no): ")
                if user_input.lower() == 'yes':
                    requests.delete(
                        f"{self.base_url}/v1/schema/{self.target_collection}",
                        headers=self.headers,
                        timeout=30
                    )
                    logger.info(f"Deleted existing collection: {self.target_collection}")
                else:
                    logger.info("Keeping existing collection. Will append data.")
                    return True
            
            # Create target schema
            response = requests.post(
                f"{self.base_url}/v1/schema",
                headers=self.headers,
                json=target_schema,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"✓ Created collection: {self.target_collection}")
                return True
            else:
                logger.error(f"Failed to create schema: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating target schema: {e}")
            return False
    
    def get_objects_with_vectors(self, limit: int, after_id: str = None) -> Optional[List[Dict]]:
        """
        Get objects from source collection with vectors using cursor-based pagination.
        Uses 'after' parameter instead of offset to avoid offset limit (max ~100k).
        
        Args:
            limit: Number of objects to fetch
            after_id: UUID to start after (cursor-based pagination)
        
        Returns:
            List of objects with properties and vectors
        """
        try:
            # Build GraphQL query with cursor-based pagination
            after_clause = f'after: "{after_id}"' if after_id else ''
            
            query = {
                "query": f"""
                {{
                  Get {{
                    {self.source_collection}(
                      limit: {limit}
                      {after_clause}
                    ) {{
                      title
                      tag
                      artist
                      year
                      views
                      features
                      lyrics
                      song_id
                      language_cld3
                      language_ft
                      language
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
                f"{self.base_url}/v1/graphql",
                headers=self.headers,
                json=query,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Check for GraphQL errors
                if "errors" in result:
                    logger.error(f"GraphQL errors: {result['errors']}")
                    return None
                
                objects = result.get("data", {}).get("Get", {}).get(self.source_collection, [])
                
                # Debug: Log what we got
                if not objects:
                    logger.warning(f"GraphQL returned empty list. Full response: {result}")
                else:
                    logger.debug(f"Fetched {len(objects)} objects successfully")
                
                return objects
            else:
                logger.error(f"Failed to fetch objects: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching objects: {e}")
            return None
    
    def batch_insert_objects(self, objects: List[Dict]) -> tuple:
        """Insert objects into target collection"""
        try:
            # Prepare batch payload
            batch_payload = []
            for obj in objects:
                additional = obj.get('_additional', {})
                
                # Remove _additional from properties
                properties = {k: v for k, v in obj.items() if k != '_additional'}
                
                batch_payload.append({
                    "class": self.target_collection,
                    "properties": properties,
                    "vector": additional.get('vector', [])
                })
            
            if not batch_payload:
                return 0, 0
            
            # Send batch insert
            response = requests.post(
                f"{self.base_url}/v1/batch/objects",
                headers=self.headers,
                json={"objects": batch_payload},
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                success = 0
                errors = 0
                
                for item in result:
                    if item.get("result", {}).get("errors"):
                        errors += 1
                    else:
                        success += 1
                
                if success == 0 and errors == 0:
                    success = len(batch_payload)
                
                return success, errors
            else:
                logger.error(f"Batch insert failed: {response.status_code}")
                return 0, len(batch_payload)
                
        except Exception as e:
            logger.error(f"Error during batch insert: {e}")
            return 0, len(objects)
    
    def copy_objects(self, total_objects: int, batch_size: int = None):
        """
        Copy objects from source to target collection with memory management.
        
        Args:
            total_objects: Total number of objects to copy
            batch_size: Batch size for fetching and inserting (defaults to config.COPY_BATCH_SIZE)
        """
        if batch_size is None:
            batch_size = getattr(config, 'COPY_BATCH_SIZE', 100)
        logger.info("=" * 70)
        logger.info(f"Starting copy operation")
        logger.info(f"Source: {self.source_collection}")
        logger.info(f"Target: {self.target_collection}")
        logger.info(f"Objects to copy: {total_objects:,}")
        logger.info(f"Batch size: {batch_size}")
        logger.info("=" * 70)
        
        total_success = 0
        total_errors = 0
        total_fetched = 0
        batch_count = 0
        last_id = None  # Cursor for pagination
        
        with tqdm(total=total_objects, desc=f"Copying to {self.target_collection}", unit="obj") as pbar:
            while total_fetched < total_objects:
                batch_count += 1
                
                # Calculate batch size for this iteration
                current_batch_size = min(batch_size, total_objects - total_fetched)
                
                # Fetch objects with vectors using cursor-based pagination
                logger.debug(f"Fetching batch {batch_count}: after_id={last_id}, limit={current_batch_size}")
                objects = self.get_objects_with_vectors(limit=current_batch_size, after_id=last_id)
                
                if objects is None:
                    logger.error(f"Failed to fetch batch {batch_count}")
                    break
                
                if not objects:
                    logger.warning(f"No more objects to fetch (got 0 objects after ID {last_id})")
                    break
                
                # Get last object's ID for next cursor
                last_id = objects[-1].get('_additional', {}).get('id')
                
                # Insert batch into target
                logger.debug(f"Inserting {len(objects)} objects into {self.target_collection}")
                success, errors = self.batch_insert_objects(objects)
                
                total_success += success
                total_errors += errors
                total_fetched += len(objects)
                
                logger.debug(f"Batch {batch_count} result: {success} successful, {errors} errors")
                
                # Update progress
                pbar.update(len(objects))
                
                # Explicit cleanup of batch data to free memory
                objects = None
                
                # Garbage collection every 10 batches (every 1000 objects)
                if batch_count % 10 == 0:
                    collected = gc.collect()
                    logger.info(f"GC after batch {batch_count}: {collected} objects freed, fetched={total_fetched:,}")
                
                # Small delay to prevent server overload
                time.sleep(0.1)
        
        # Final garbage collection
        logger.info("Running final garbage collection...")
        for i in range(2):
            collected = gc.collect()
            logger.info(f"  Final GC pass {i+1}: {collected} objects collected")
        
        logger.info("=" * 70)
        logger.info(f"Copy operation complete!")
        logger.info(f"Total copied: {total_success:,}")
        logger.info(f"Total errors: {total_errors:,}")
        logger.info("=" * 70)
        
        return total_success, total_errors


def main():
    """Main function"""
    print("=" * 70)
    print("WEAVIATE COLLECTION COPIER")
    print("=" * 70)
    
    # Configuration
    print("\nConfiguration:")
    print(f"Source collection: {config.WEAVIATE_CLASS_NAME}")
    print(f"Weaviate URL: {config.WEAVIATE_URL}")
    
    # Get target collection name
    print("\n" + "=" * 70)
    target_collection = input("Enter target collection name: ").strip()
    
    if not target_collection:
        print("❌ Target collection name cannot be empty")
        return 1
    
    # Get number of objects to copy
    try:
        num_objects = int(input("Enter number of objects to copy: "))
        if num_objects <= 0:
            print("❌ Number of objects must be positive")
            return 1
    except ValueError:
        print("❌ Invalid number")
        return 1
    
    # Confirm
    print("\n" + "=" * 70)
    print("Summary:")
    print(f"  From: {config.WEAVIATE_CLASS_NAME}")
    print(f"  To: {target_collection}")
    print(f"  Objects: {num_objects:,}")
    print("=" * 70)
    
    confirm = input("\nProceed with copy? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("❌ Copy cancelled")
        return 0
    
    # Create copier
    copier = CollectionCopier(config.WEAVIATE_CLASS_NAME, target_collection)
    
    # Create target schema
    print("\n📝 Creating target collection schema...")
    if not copier.create_target_schema():
        print("❌ Failed to create target schema")
        return 1
    
    # Copy objects
    print("\n📦 Starting copy operation...")
    success, errors = copier.copy_objects(num_objects, batch_size=2000)
    
    if errors == 0:
        print(f"\n✅ Successfully copied {success:,} objects!")
    else:
        print(f"\n⚠️  Copied {success:,} objects with {errors:,} errors")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

