import unittest
import tempfile
from pathlib import Path
from mesh_registry import MeshRegistry

class TestMeshRegistryGovernance(unittest.TestCase):
    def test_mesh_nodes_loaded_correctly(self):
        registry = MeshRegistry()
        expected_nodes = [
            "sweepsync", "holixtica-finance", "actor-web-automation",
            "living-system", "holixtica-ledger", "holixtica-core", "widow-ui",
            "notebooklm-synthesizer"
        ]
        for node_id in expected_nodes:
            self.assertIn(node_id, registry.nodes)

    def test_route_rejection_for_undeclared_events(self):
        registry = MeshRegistry()
        for node_id in registry.nodes:
            res = registry.type_check_and_route("undeclared.event.topic", node_id, {"data": "test"})
            self.assertEqual(res["status"], "denied")

    def test_cross_tier_denial_for_presentation_node(self):
        registry = MeshRegistry()
        # widow-ui (presentation tier) attempting to emit ledger.entry (regulated event)
        res = registry.type_check_and_route("ledger.entry", "widow-ui", {"amount": 1000})
        self.assertEqual(res["status"], "denied")
        self.assertIn("unauthorized", res["reason"])

    def test_symlink_and_traversal_write_scope_escape(self):
        registry = MeshRegistry()
        sweepsync = registry.get_node("sweepsync")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            (base_dir / "runtime").mkdir()
            (base_dir / "protected").mkdir()

            # Valid path inside write scope
            self.assertTrue(sweepsync.is_path_in_write_scope("runtime/cache.json", base_dir=base_dir))
            
            # Symlink / relative traversal escape attempt
            self.assertFalse(sweepsync.is_path_in_write_scope("runtime/../protected/core.py", base_dir=base_dir))

    def test_healthcheck_quarantines_node_from_dispatch(self):
        registry = MeshRegistry()
        node = registry.get_node("widow-ui")
        node.healthcheck = "exit 1"  # Failing command
        
        success = registry.run_healthcheck("widow-ui")
        self.assertFalse(success)
        self.assertTrue(node.is_quarantined)

        # Quarantined node rejects event dispatch
        self.assertFalse(node.can_accept_event("state.adapted"))
        self.assertFalse(node.can_emit_event("ui.command"))

    def test_e2e_golden_path_pipeline(self):
        registry = MeshRegistry()
        results = registry.execute_non_monetary_provenance_flow({"payload": "non_monetary_provenance_test"})
        self.assertEqual(len(results), 6)
        for step in results:
            self.assertEqual(step["status"], "routed")
            self.assertTrue(len(step["recipients"]) > 0)

    def test_six_clause_boolean_conjunction_predicate(self):
        registry = MeshRegistry()
        # Valid routing: holixtica-core emitting domain.normalized to holixtica-finance
        res_valid = registry.is_event_allowed("domain.normalized", "holixtica-core", "holixtica-finance")
        self.assertTrue(res_valid["allowed"])

        # Clause 1 Failure: Unregistered node
        res_c1 = registry.is_event_allowed("domain.normalized", "ghost-node", "holixtica-finance")
        self.assertFalse(res_c1["allowed"])
        self.assertIn("Clause 1", res_c1["reason"])

        # Clause 2/4 Failure: Unauthorized trust tier emission (widow-ui emitting ledger.entry)
        res_c2 = registry.is_event_allowed("ledger.entry", "widow-ui", "holixtica-ledger")
        self.assertFalse(res_c2["allowed"])
        self.assertIn("Clause 2/4", res_c2["reason"])

        # Clause 3 Failure: Recipient does not accept event
        res_c3 = registry.is_event_allowed("ui.ack", "widow-ui", "actor-web-automation")
        self.assertFalse(res_c3["allowed"])
        self.assertIn("Clause 3/6", res_c3["reason"])

        # Clause 6 Failure: Quarantined node
        widow = registry.get_node("widow-ui")
        widow.is_quarantined = True
        res_c6 = registry.is_event_allowed("state.adapted", "living-system", "widow-ui")
        self.assertFalse(res_c6["allowed"])
        self.assertIn("Clause 3/6", res_c6["reason"])

if __name__ == "__main__":
    unittest.main()
