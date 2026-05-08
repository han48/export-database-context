import json

with open('outputs/knowledge_graph_feelcycle-mob-db-dev_schema.json') as f:
    data = json.load(f)

print("Valid JSON!")
nodes = data["nodes"]
edges = data["edges"]
print(f"Nodes: {len(nodes)}")
print(f"Edges: {len(edges)}")

# Check all edge references exist in nodes
node_ids = {n["id"] for n in nodes}
missing = set()
for e in edges:
    if e["source"] not in node_ids:
        missing.add(f"source: {e['source']}")
    if e["target"] not in node_ids:
        missing.add(f"target: {e['target']}")

if missing:
    print(f"MISSING node references ({len(missing)}):")
    for m in sorted(missing):
        print(f"  {m}")
else:
    print("All edge references valid!")
