import unittest
from pathlib import Path
from bin.holixtica_gemini_bridge import HolixticaGeminiBridge
from tools.holixtica_browser_engine import HolixticaBrowserEngine

class TestHolixticaBridge(unittest.TestCase):
    def test_gemini_bridge_binary_resolution(self):
        bridge = HolixticaGeminiBridge()
        self.assertTrue(bridge.ls_binary.exists())
        self.assertIn("language_server", str(bridge.ls_binary))

    def test_browser_engine_endpoint_discovery(self):
        engine = HolixticaBrowserEngine()
        endpoint = engine.discover_active_cdp_endpoint()
        self.assertTrue(endpoint.startswith("ws://") or endpoint.startswith("http://"))

if __name__ == "__main__":
    unittest.main()
