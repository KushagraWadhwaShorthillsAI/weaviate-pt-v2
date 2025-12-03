import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from azure.storage.blob import BlobServiceClient
import config

# Replace with your values
connection_string = config.AZURE_BLOB_CONNECTION_STRING
container_name = config.AZURE_BLOB_CONTAINER_NAME

try:
    # Create the BlobServiceClient object using the connection string
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)

    # Get container client
    container_client = blob_service_client.get_container_client(container_name)

    # List all blobs in the container
    print(f"Listing blobs in container: {container_name}\n")
    blob_list = container_client.list_blobs()

    for blob in blob_list:
        print(f"- {blob.name}")

except Exception as e:
    print("Error:", e)