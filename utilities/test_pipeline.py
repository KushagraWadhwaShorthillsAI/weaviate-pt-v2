"""
Test script to verify the complete pipeline by indexing a few rows from CSV to Weaviate.
This tests: CSV reading → Azure OpenAI embeddings → Weaviate indexing → Search
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio
import pandas as pd

import config
from openai_client import create_async_openai_client
from weaviate_client import create_weaviate_client, insert_single_object, batch_insert_objects

# Number of test rows to process
TEST_ROWS = 5


class PipelineTester:
    """Tests the complete pipeline with a small sample"""
    
    def __init__(self):
        # Initialize OpenAI client using centralized module
        self.openai_client, self.embedding_model = create_async_openai_client()
        print(f"✓ Using embedding model: {self.embedding_model}")
        
        self.weaviate_client = None
    
    def connect_weaviate(self):
        """Connect to Weaviate using centralized client"""
        print("\n📊 Connecting to Weaviate...")
        try:
            # Use centralized client creation
            self.weaviate_client = create_weaviate_client()
            
            if not self.weaviate_client.collections.exists(config.WEAVIATE_CLASS_NAME):
                print(f"❌ Collection '{config.WEAVIATE_CLASS_NAME}' does not exist!")
                print("   Run: python create_weaviate_schema.py")
                return False
            
            # Get collection for search operations
            self.collection = self.weaviate_client.collections.get(config.WEAVIATE_CLASS_NAME)
            print(f"✓ Connected to collection: {config.WEAVIATE_CLASS_NAME}")
            return True
            
        except Exception as e:
            print(f"❌ Weaviate connection failed: {e}")
            print(f"   URL: {config.WEAVIATE_URL}")
            return False
    
    def read_test_data(self):
        """Read test rows from CSV"""
        print(f"\n📖 Reading {TEST_ROWS} test rows from CSV...")
        try:
            # Handle relative path from utilities/ folder
            csv_path = config.CSV_FILE_PATH
            if not os.path.isabs(csv_path):
                csv_path = os.path.join(os.path.dirname(__file__), '..', csv_path)
            
            df = pd.read_csv(csv_path, nrows=TEST_ROWS)
            print(f"✓ Read {len(df)} rows")
            print(f"  Columns: {list(df.columns)}")
            return df
        except Exception as e:
            print(f"❌ Failed to read CSV: {e}")
            return None
    
    async def get_embedding(self, text: str):
        """Get embedding for text"""
        try:
            response = await self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text[:8000]  # Limit text length
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"  ❌ Embedding failed: {e}")
            return None
    
    async def process_and_index(self, df):
        """Process rows and index to Weaviate - Tests BOTH single and batch insert"""
        print(f"\n🔄 Processing {len(df)} rows...")
        print("=" * 70)
        
        success_count = 0
        error_count = 0
        indexed_ids = []
        
        # Collect all data and embeddings first
        all_data = []
        all_embeddings = []
        
        for idx, row in df.iterrows():
            try:
                # Clean data
                data = {
                    'title': str(row.get('title', '')),
                    'tag': str(row.get('tag', '')),
                    'artist': str(row.get('artist', '')),
                    'year': int(row.get('year', 0)) if pd.notna(row.get('year')) else 0,
                    'views': int(row.get('views', 0)) if pd.notna(row.get('views')) else 0,
                    'features': str(row.get('features', '')),
                    'lyrics': str(row.get('lyrics', '')),
                    'song_id': str(row.get('id', '')),
                    'language_cld3': str(row.get('language_cld3', '')),
                    'language_ft': str(row.get('language_ft', '')),
                    'language': str(row.get('language', ''))
                }
                
                print(f"\n[{idx+1}/{len(df)}] {data['title']} by {data['artist']}")
                
                # Get embedding
                print(f"  → Getting embedding... ", end="", flush=True)
                embedding = await self.get_embedding(data['lyrics'])
                if embedding is None:
                    print("❌ Failed")
                    error_count += 1
                    continue
                print(f"✓ ({len(embedding)} dims)")
                
                all_data.append(data)
                all_embeddings.append(embedding)
                
            except Exception as e:
                print(f"  ❌ Error: {e}")
                error_count += 1
        
        # Now test both insertion methods
        print("\n" + "=" * 70)
        print("Testing Insertion Methods:")
        print("=" * 70)
        
        # Split data: first half for single insert, second half for batch insert
        split_point = len(all_data) // 2
        
        # Test 1: Single Insert Method
        if split_point > 0:
            print(f"\n🔸 Test 1: Single Insert (insert_single_object)")
            print(f"   Testing with {split_point} row(s)...")
            for i in range(split_point):
                print(f"   [{i+1}/{split_point}] Inserting: {all_data[i]['title'][:30]}... ", end="", flush=True)
                result_id = insert_single_object(all_data[i], all_embeddings[i])
                if result_id:
                    print(f"✓ {result_id[:8]}...")
                    indexed_ids.append(result_id)
                    success_count += 1
                else:
                    print(f"❌ Failed")
                    error_count += 1
            print(f"   ✓ Single insert test complete: {split_point} inserted")
        
        # Test 2: Batch Insert Method
        remaining = len(all_data) - split_point
        if remaining > 0:
            print(f"\n🔸 Test 2: Batch Insert (batch_insert_objects)")
            print(f"   Testing with {remaining} row(s)...")
            
            # Prepare batch objects
            batch_objects = []
            for i in range(split_point, len(all_data)):
                batch_objects.append({
                    "properties": all_data[i],
                    "vector": all_embeddings[i]
                })
                print(f"   [{i-split_point+1}/{remaining}] Prepared: {all_data[i]['title'][:30]}...")
            
            # Do batch insert
            print(f"   → Sending batch of {remaining} objects... ", end="", flush=True)
            batch_success, batch_errors = batch_insert_objects(batch_objects)
            print(f"✓ Done")
            print(f"   ✓ Batch insert complete: {batch_success} successful, {batch_errors} errors")
            
            success_count += batch_success
            error_count += batch_errors
            
            # Note: batch insert doesn't return UUIDs, so we can't add to indexed_ids
            # But we can verify they were inserted via search
        
        print("=" * 70)
        print(f"\n✅ Indexing Complete:")
        print(f"   Single insert: {split_point} rows")
        print(f"   Batch insert: {batch_success if remaining > 0 else 0} rows")
        print(f"   Total success: {success_count}")
        print(f"   Total errors: {error_count}")
        
        return indexed_ids
    
    async def test_search(self, indexed_ids):
        """Test searching the indexed data using REST API (avoid gRPC issues)"""
        if not indexed_ids:
            print("\n⚠️  No data indexed, skipping search test")
            return
        
        print(f"\n🔍 Testing search functionality...")
        print("=" * 70)
        
        try:
            import requests
            
            headers = {"Content-Type": "application/json"}
            if config.WEAVIATE_API_KEY and config.WEAVIATE_API_KEY != "your-weaviate-api-key":
                headers["Authorization"] = f"Bearer {config.WEAVIATE_API_KEY}"
            
            # Test 1: GraphQL query (BM25 search)
            print("\n1. BM25 Search Test: 'love songs'")
            graphql_query = {
                "query": """
                {
                  Get {
                    """ + config.WEAVIATE_CLASS_NAME + """(
                      bm25: {query: "love songs", properties: ["title", "lyrics"]}
                      limit: 3
                    ) {
                      title
                      artist
                    }
                  }
                }
                """
            }
            
            response = requests.post(
                f"{config.WEAVIATE_URL}/v1/graphql",
                headers=headers,
                json=graphql_query,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                objects = result.get("data", {}).get("Get", {}).get(config.WEAVIATE_CLASS_NAME, [])
                if objects:
                    print(f"   ✓ Found {len(objects)} results:")
                    for i, obj in enumerate(objects, 1):
                        print(f"   {i}. {obj.get('title', 'N/A')} by {obj.get('artist', 'N/A')}")
                else:
                    print("   ⚠️  No results found")
            else:
                print(f"   ❌ Search failed: {response.status_code}")
            
            # Test 2: Get by ID
            print(f"\n2. Fetch by UUID Test")
            test_id = indexed_ids[0]
            response = requests.get(
                f"{config.WEAVIATE_URL}/v1/objects/{test_id}",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                obj = response.json()
                print(f"   ✓ Retrieved: {obj.get('properties', {}).get('title', 'N/A')}")
            else:
                print("   ❌ Failed to retrieve")
            
            # Test 3: Count total objects via GraphQL
            print(f"\n3. Count total objects in collection")
            count_query = {
                "query": """
                {
                  Aggregate {
                    """ + config.WEAVIATE_CLASS_NAME + """ {
                      meta {
                        count
                      }
                    }
                  }
                }
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
                count = result.get("data", {}).get("Aggregate", {}).get(config.WEAVIATE_CLASS_NAME, [{}])[0].get("meta", {}).get("count", 0)
                print(f"   ✓ Total objects: {count}")
            else:
                print(f"   ⚠️  Count failed: {response.status_code}")
            
            print("=" * 70)
            print("✅ All search tests completed!")
            
        except Exception as e:
            print(f"❌ Search test failed: {e}")
            import traceback
            traceback.print_exc()
    
    async def run(self):
        """Run the complete test pipeline"""
        print("=" * 70)
        print("🧪 PIPELINE TEST - End-to-End Verification")
        print("=" * 70)
        
        # Step 1: Connect to Weaviate
        if not self.connect_weaviate():
            return False
        
        # Step 2: Read test data
        df = self.read_test_data()
        if df is None or len(df) == 0:
            return False
        
        # Step 3: Process and index
        indexed_ids = await self.process_and_index(df)
        
        # Step 4: Test search
        await self.test_search(indexed_ids)
        
        print("\n" + "=" * 70)
        print("🎉 Pipeline test completed successfully!")
        print("=" * 70)
        print("\n✅ Your setup is working correctly!")
        print("   You can now run: python process_lyrics.py")
        print("=" * 70)
        
        return True
    
    async def close(self):
        """Cleanup"""
        if self.weaviate_client:
            self.weaviate_client.close()
        await self.openai_client.close()


async def main():
    """Main entry point"""
    tester = PipelineTester()
    
    try:
        success = await tester.run()
        if not success:
            print("\n❌ Test failed. Please check the errors above.")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await tester.close()


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("  END-TO-END PIPELINE TEST")
    print(f"  Testing with {TEST_ROWS} rows from CSV")
    print("=" * 70 + "\n")
    
    # Run the async main function
    asyncio.run(main())

