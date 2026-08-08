import unittest
from mesh_registry import MeshRegistry

class TestMeshRegistry(unittest.TestCase):
    def test_mesh_nodes_loaded_correctly(self):
        registry = MeshRegistry()
        expected_nodes = [
            "sweepsync", "holixtica-finance", "actor-web-automation",
            "living-system", "holixtica-ledger", "holixtica-core", "widow-ui"
        ]
        for node_id in expected_nodes:
            self.assertIn(node_id, registry.nodes)

    def test_trust_tiers_and_roles(self):
        registry = MeshRegistry()
        living = registry.get_node("living-system")
        self.assertEqual(living.trust_tier, "core")
        self.assertEqual(living.role, "adaptive-state")

        ledger = registry.get_node("holixtica-ledger")
        self.assertEqual(ledger.trust_tier, "regulated")
        self.assertEqual(ledger.role, "ledger-authority")

        widow = registry.get_node("widow-ui")
        self.assertEqual(widow.trust_tier, "presentation")
        self.assertEqual(widow.role, "operator-interface")

    def test_event_routing(self):
        registry = MeshRegistry()
        sync_subscribers = registry.route_event("sync.completed")
        self.assertIn("living-system", sync_subscribers)
        self.assertIn("holixtica-ledger", sync_subscribers)
        self.assertIn("widow-ui", sync_subscribers)

        adapted_subscribers = registry.route_event("state.adapted")
        self.assertEqual(adapted_subscribers, ["widow-ui"])

    def test_write_scope_enforcement(self):
        registry = MeshRegistry()
        living = registry.get_node("living-system")
        self.assertTrue(living.is_path_in_write_scope("models/weights.bin"))
        self.assertFalse(living.is_path_in_write_scope("protected/core.py"))

if __name__ == "__main__":
    unittest.main()
