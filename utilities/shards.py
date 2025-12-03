import weaviate
import json

# Connect to your Weaviate instance
client = weaviate.Client("http://20.161.96.75")

# Fetch node information
nodes_info = client.misc.get_nodes()

# Pretty print shard distribution per node
print(json.dumps(nodes_info, indent=2))

# Optional: Summarize shard distribution
print("\n=== Shard Distribution Summary ===")
for node in nodes_info['nodes']:
    print(f"\n🖥️ Node: {node['name']} ({node['status']})")
    for class_name, shards in node.get('shards', {}).items():
        shard_names = [shard['name'] for shard in shards]
        print(f"  • {class_name}: {', '.join(shard_names)}")

