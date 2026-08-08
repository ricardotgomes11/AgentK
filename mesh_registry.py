"""
AgentK Federated Mesh Registry
==============================
Manages node declarations, trust tiers, event subscriptions, healthchecks,
and write scope boundary enforcement for AgentK peer nodes.
"""

import os
import sys
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional

CONFIG_PATH = Path(__file__).resolve().parent / "config" / "mesh_nodes.yaml"


class MeshNode:
    def __init__(self, node_data: Dict[str, Any]):
        self.id: str = node_data["id"]
        self.repo: str = node_data["repo"]
        self.role: str = node_data["role"]
        self.trust_tier: str = node_data["trust_tier"]
        self.healthcheck: str = node_data["healthcheck"]
        self.accepts: List[str] = node_data.get("accepts", [])
        self.emits: List[str] = node_data.get("emits", [])
        self.write_scope: List[str] = node_data.get("write_scope", [])

    def can_accept_event(self, event_topic: str) -> bool:
        return event_topic in self.accepts

    def is_path_in_write_scope(self, target_path: str) -> bool:
        norm_path = target_path.lstrip("/")
        return any(norm_path.startswith(ws.lstrip("/")) for ws in self.write_scope)


class MeshRegistry:
    def __init__(self, config_path: Path = CONFIG_PATH):
        self.config_path = config_path
        self.nodes: Dict[str, MeshNode] = {}
        self.load_nodes()

    def load_nodes(self):
        if not self.config_path.exists():
            return
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            for node_data in data.get("nodes", []):
                node = MeshNode(node_data)
                self.nodes[node.id] = node

    def get_node(self, node_id: str) -> Optional[MeshNode]:
        return self.nodes.get(node_id)

    def route_event(self, event_topic: str) -> List[str]:
        """Returns IDs of nodes authorized to receive event_topic."""
        return [node_id for node_id, node in self.nodes.items() if node.can_accept_event(event_topic)]


if __name__ == "__main__":
    registry = MeshRegistry()
    print(f"[MESH REGISTRY] Loaded {len(registry.nodes)} nodes: {list(registry.nodes.keys())}")
    for nid, n in registry.nodes.items():
        print(f" - Node {nid} ({n.trust_tier}): accepts {n.accepts}, emits {n.emits}")
