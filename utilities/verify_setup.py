"""
Quick verification script to test configuration before running the main processor.
Tests connectivity to OpenAI and Weaviate.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import sys
import logging
import config
from openai_client import create_sync_openai_client
from weaviate_client import create_weaviate_client

# Setup logging for verify_setup
logging.basicConfig(level=logging.WARNING)  # Only show warnings and errors

def test_openai():
    """Test OpenAI API connection using centralized client"""
    try:
        client, model = create_sync_openai_client()
        
        # Try a simple embedding request to verify
        response = client.embeddings.create(
            model=model,
            input="test"
        )
        
        if config.USE_AZURE_OPENAI:
            print("✅ Azure OpenAI connection successful!")
            print(f"   Endpoint: {config.AZURE_OPENAI_ENDPOINT}")
            print(f"   Deployment: {config.AZURE_OPENAI_DEPLOYMENT_NAME}")
            print(f"   API Version: {config.AZURE_OPENAI_API_VERSION}")
        else:
            print("✅ OpenAI connection successful!")
            print(f"   Model: {config.OPENAI_MODEL}")
        
        print(f"   Embedding dimension: {len(response.data[0].embedding)}")
        return True
        
    except Exception as e:
        print(f"❌ OpenAI connection failed: {e}")
        if config.USE_AZURE_OPENAI:
            print("   Please check your Azure OpenAI settings in config.py")
        else:
            print("   Please check your OPENAI_API_KEY in config.py")
        return False

def test_weaviate():
    """Test Weaviate connection using centralized client"""
    print("\nTesting Weaviate connection...")
    try:
        # Use centralized client creation
        client = create_weaviate_client()
        
        # Test if server is reachable
        if client.is_ready():
            print("✅ Weaviate connection successful!")
            print(f"   URL: {config.WEAVIATE_URL}")
            
            # Check if collection exists
            if client.collections.exists(config.WEAVIATE_CLASS_NAME):
                print(f"   ✅ Collection '{config.WEAVIATE_CLASS_NAME}' exists and ready")
                print("      Existing data will be preserved, new data will be added")
            else:
                print(f"   ⚠️  Collection '{config.WEAVIATE_CLASS_NAME}' does not exist")
                print("      Run 'python create_weaviate_schema.py' to create it")
            
            client.close()
            return True
        else:
            print("❌ Weaviate server not ready")
            client.close()
            return False
            
    except Exception as e:
        print(f"❌ Weaviate connection failed: {e}")
        print(f"   URL: {config.WEAVIATE_URL}")
        print("   Please check your WEAVIATE_URL in config.py")
        return False

def test_csv():
    """Test CSV file accessibility"""
    print("\nTesting CSV file...")
    try:
        import os
        
        # Handle relative path from utilities/ folder
        csv_path = config.CSV_FILE_PATH
        if not os.path.isabs(csv_path):
            # If relative path, check from parent directory
            csv_path = os.path.join(os.path.dirname(__file__), '..', csv_path)
        
        if not os.path.exists(csv_path):
            print(f"❌ CSV file not found: {config.CSV_FILE_PATH}")
            print(f"   Looked at: {csv_path}")
            print(f"   Note: CSV file should be in project root: song_lyrics.csv")
            return False
        
        # Try to read first row
        import pandas as pd
        df = pd.read_csv(csv_path, nrows=1)
        print(f"✅ CSV file accessible!")
        print(f"   Path: {config.CSV_FILE_PATH}")
        print(f"   Columns: {list(df.columns)}")
        
        # Check if expected columns exist
        expected_cols = set(config.CSV_COLUMNS)
        actual_cols = set(df.columns)
        missing = expected_cols - actual_cols
        if missing:
            print(f"   ⚠️  Missing columns: {missing}")
        
        return True
    except Exception as e:
        print(f"❌ CSV file test failed: {e}")
        return False

def main():
    """Run all verification tests"""
    print("=" * 60)
    print("Setup Verification")
    print("=" * 60)
    
    results = []
    results.append(("OpenAI", test_openai()))
    results.append(("Weaviate", test_weaviate()))
    results.append(("CSV File", test_csv()))
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    all_passed = all(result for _, result in results)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:20} {status}")
    
    print("=" * 60)
    
    if all_passed:
        print("\n🎉 All tests passed! You can now run: python process_lyrics.py")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above before proceeding.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

