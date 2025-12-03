import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config
from azure.storage.blob import BlobServiceClient

# Replace with your values
connection_string = config.AZURE_BLOB_CONNECTION_STRING
container_name = config.AZURE_BLOB_CONTAINER_NAME
prefix_to_delete = ".." 

try:
    # Connect to the blob service
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service_client.get_container_client(container_name)

    # List blobs under the given prefix
    print(f"Fetching blobs under prefix: {prefix_to_delete}")
    blobs_to_delete = container_client.list_blobs(name_starts_with=prefix_to_delete)

    deleted_count = 0
    for blob in blobs_to_delete:
        blob_client = container_client.get_blob_client(blob.name)
        blob_client.delete_blob()
        deleted_count += 1
        print(f"Deleted: {blob.name}")

    print(f"\n✅ Deleted {deleted_count} blobs under prefix '{prefix_to_delete}'")

except Exception as e:
    print("Error:", e)
