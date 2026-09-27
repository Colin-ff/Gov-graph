# def test_health_ok(client):
#     resp = client.get("/health")
#     assert resp.status_code == 200
#     body = resp.get_json()
#     assert body["status"] == "ok"
#     assert body["service"] == "govgraph-api"


# def test_graph_empty_by_default(client):
#     resp = client.get("/api/graph")
#     assert resp.status_code == 200
#     body = resp.get_json()
#     # Shape follows nodes_edges_visualisation.json — the key is "relations".
#     assert body == {"nodes": [], "relations": []}
