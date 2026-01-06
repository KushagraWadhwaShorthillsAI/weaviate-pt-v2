import requests

WEAVIATE_URL = "http://20.161.96.75"
resp = requests.get(f"{WEAVIATE_URL}/v1/nodes?output=verbose")
resp.raise_for_status()
data = resp.json()
print(data)

