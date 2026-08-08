import unittest
from mesh_registry import MeshRegistry

class TestMeshRegistry(unittest.TestCase):
    def test_mesh_nodes_loaded_correctly(self):
        registry = MeshRegistry()
        self.assertIn("sweepsync", registry.nodes)
        self.assertIn("holixtica-finance", registry.nodes)
        self.assertIn("actor-web-automation", registry.nodes)

    def test_trust_tiers_and_roles(self):
        registry = MeshRegistry()
        sweepsync = registry.get_node("sweepsync")
        self.assertEqual(sweepsync.trust_tier, "core")
        self.assertEqual(sweepsync.role, "event-sync")

        finance = registry.get_node("holixtica-finance")
        self.assertEqual(finance.trust_tier, "regulated")

        web = registry.get_node("actor-web-automation")
        self.assertEqual(web.trust_tier, "isolated")

    def test_event_routing(self):
        registry = MeshRegistry()
        target_nodes = registry.route_event("payment.authorize")
        self.assertEqual(target_nodes, ["holixtica-finance"])

        sync_nodes = registry.route_event("state.changed")
        self.assertEqual(sync_nodes, ["sweepsync"])

    def test_write_scope_enforcement(self):
        registry = MeshRegistry()
        sweepsync = registry.get_node("sweepsync")
        self.assertTrue(sweepsync.is_path_in_write_scope("runtime/state.json"))
        self.assertFalse(sweepsync.is_path_in_write_scope("protected/core.py"))

if __name__ == "__main__":
    unittest.main()
