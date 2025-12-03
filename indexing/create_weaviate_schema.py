"""
Script to create Weaviate schema with proper tokenization and indexing configuration.
Run this before starting the main processing to ensure schema is set up correctly.
"""


import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import requests
import json as json_lib
import config
import logging
from weaviate_client import create_weaviate_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_optimized_schema():
    """Create Weaviate schema with optimized tokenization and indexing"""
    
    try:
        # Use centralized client creation
        client = create_weaviate_client()
        
        # Check if authentication is needed
        use_auth = config.WEAVIATE_API_KEY and config.WEAVIATE_API_KEY != "your-weaviate-api-key"
        
        # Check if collection already exists
        if client.collections.exists(config.WEAVIATE_CLASS_NAME):
            logger.warning(f"Collection '{config.WEAVIATE_CLASS_NAME}' already exists!")
            response = input("Do you want to delete and recreate it? (yes/no): ")
            if response.lower() == 'yes':
                client.collections.delete(config.WEAVIATE_CLASS_NAME)
                logger.info(f"Deleted existing collection '{config.WEAVIATE_CLASS_NAME}'")
            else:
                logger.info("Keeping existing collection. Exiting.")
                client.close()
                return
        
        # Create collection schema using REST API (for BlockMaxWAND control)
        schema_config = {
            "class": config.WEAVIATE_CLASS_NAME,
            "description": "Song lyrics with metadata and embeddings",
            
            # Sharding configuration
            "shardingConfig": {
                "desiredCount": 3
            },
            
            # Replication configuration
            "replicationConfig": {
                "asyncEnabled": True,
                "factor": 1
            },
            
            # Inverted index configuration with BlockMaxWAND disabled
            "invertedIndexConfig": {
                "usingBlockMaxWAND": False  # Explicitly disable BlockMaxWAND
            },
            
            # Properties with specific tokenization
            "properties": [
                # Searchable text fields with WORD tokenization
                {
                    "name": "title",
                    "dataType": ["text"],
                    "description": "Song title",
                    "indexSearchable": True,
                    "indexFilterable": False,
                    "tokenization": "word"
                },
                {
                    "name": "lyrics",
                    "dataType": ["text"],
                    "description": "Song lyrics content",
                    "indexSearchable": True,
                    "indexFilterable": False,
                    "tokenization": "word"
                },
                
                # Filterable fields with FIELD tokenization
                {
                    "name": "tag",
                    "dataType": ["text"],
                    "description": "Genre/category tag",
                    "indexSearchable": False,
                    "indexFilterable": True,
                    "tokenization": "field"
                },
                {
                    "name": "artist",
                    "dataType": ["text"],
                    "description": "Artist name",
                    "indexSearchable": False,
                    "indexFilterable": True,
                    "tokenization": "field"
                },
                {
                    "name": "features",
                    "dataType": ["text"],
                    "description": "Featured artists",
                    "indexSearchable": False,
                    "indexFilterable": True,
                    "tokenization": "field"
                },
                {
                    "name": "song_id",
                    "dataType": ["text"],
                    "description": "Unique song identifier (may include _chunkN suffix for split lyrics)",
                    "indexSearchable": False,
                    "indexFilterable": True,
                    "tokenization": "field"
                },
                {
                    "name": "language_cld3",
                    "dataType": ["text"],
                    "description": "Language detected by CLD3",
                    "indexSearchable": False,
                    "indexFilterable": True,
                    "tokenization": "field"
                },
                {
                    "name": "language_ft",
                    "dataType": ["text"],
                    "description": "Language detected by FastText",
                    "indexSearchable": False,
                    "indexFilterable": True,
                    "tokenization": "field"
                },
                {
                    "name": "language",
                    "dataType": ["text"],
                    "description": "Primary language",
                    "indexSearchable": False,
                    "indexFilterable": True,
                    "tokenization": "field"
                },
                
                # Numeric fields (automatically filterable with range filter support)
                {
                    "name": "year",
                    "dataType": ["int"],
                    "description": "Release year",
                    "indexFilterable": True,
                    "indexRangeFilters": True
                },
                {
                    "name": "views",
                    "dataType": ["int"],
                    "description": "Number of views",
                    "indexFilterable": True,
                    "indexRangeFilters": True
                }
            ]
        }
        
        # Create schema using REST API for full control
        headers = {"Content-Type": "application/json"}
        if use_auth:
            headers["Authorization"] = f"Bearer {config.WEAVIATE_API_KEY}"
        
        response = requests.post(
            f"{config.WEAVIATE_URL}/v1/schema",
            headers=headers,
            json=schema_config
        )
        
        if response.status_code == 200:
            logger.info("Collection created successfully via REST API")
        else:
            logger.error(f"Failed to create collection: {response.status_code}")
            logger.error(f"Response: {response.text}")
            client.close()
            raise Exception(f"Schema creation failed: {response.text}")
        
        logger.info("=" * 70)
        logger.info(f"✅ Successfully created collection: {config.WEAVIATE_CLASS_NAME}")
        logger.info("=" * 70)
        logger.info("\nConfiguration Summary:")
        logger.info(f"  - Sharding: 3 shards")
        logger.info(f"  - Replication: Factor of 1")
        logger.info(f"  - Vectorizer: None (external embeddings)")
        logger.info(f"  - BM25: b=0.75, k1=1.2")
        logger.info(f"  - usingBlockMaxWAND: false ✅ (Explicitly disabled)")
        logger.info(f"  - Stopwords: English preset")
        logger.info(f"\nSearchable Fields (word tokenization):")
        logger.info(f"  - title")
        logger.info(f"  - lyrics")
        logger.info(f"\nFilterable Fields (field tokenization):")
        logger.info(f"  - tag, artist, features, song_id")
        logger.info(f"  - language_cld3, language_ft, language")
        logger.info(f"\nNumeric Fields (with range filter indexing):")
        logger.info(f"  - year (indexRangeFilters=true)")
        logger.info(f"  - views (indexRangeFilters=true)")
        logger.info("=" * 70)
        
        # Close connection
        client.close()
        logger.info("\n✅ Schema creation complete! You can now run: python process_lyrics.py")
        
    except Exception as e:
        logger.error(f"Error creating schema: {e}")
        logger.error("\nTroubleshooting:")
        logger.error("1. Make sure Weaviate is running")
        logger.error("2. Check WEAVIATE_URL in config.py")
        logger.error("3. Verify network connectivity")
        raise


if __name__ == "__main__":
    print("=" * 70)
    print("Weaviate Schema Creator")
    print("=" * 70)
    print(f"\nWeaviate URL: {config.WEAVIATE_URL}")
    print(f"Collection Name: {config.WEAVIATE_CLASS_NAME}")
    print("\nThis will create a new collection with optimized indexing.")
    print("=" * 70)
    
    create_optimized_schema()

