"""
AgentK Federated Mesh Registry — Runtime Governance Engine
=========================================================
Manages node declarations, trust tiers, active healthcheck quarantining,
cross-tier event authorization, symlink-proof write scope enforcement,
and end-to-end golden path execution pipelines for AgentK peer nodes.
"""

import os
import sys
import yaml
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

from sovereign_pipeline_executor import SovereignPipelineExecutor

CONFIG_PATH = Path(__file__).resolve().parent / "config" / "mesh_nodes.yaml"

# Tier authority levels: presentation (0) < isolated (1) < regulated (2) < core (3)
TIER_HIERARCHY = {
    "presentation": 0,
    "isolated": 1,
    "regulated": 2,
    "core": 3,
}

EVENT_MIN_TIER = {
    "payment.authorize": "regulated",
    "settlement.reconcile": "regulated",
    "ledger.entry": "regulated",
    "ledger.committed": "regulated",
    "domain.command": "core",
    "domain.normalized": "core",
    "ui.command": "presentation",
    "ui.ack": "presentation",
}


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
        self.is_quarantined: bool = False

    def can_accept_event(self, event_topic: str) -> bool:
        if self.is_quarantined:
            return False
        return event_topic in self.accepts

    def can_emit_event(self, event_topic: str) -> bool:
        if self.is_quarantined:
            return False
        if event_topic not in self.emits:
            return False
        # Cross-tier enforcement: check required tier vs node tier
        min_tier = EVENT_MIN_TIER.get(event_topic, "isolated")
        if TIER_HIERARCHY.get(self.trust_tier, 0) < TIER_HIERARCHY.get(min_tier, 0):
            return False
        return True

    def is_path_in_write_scope(self, target_path: str, base_dir: Optional[Path] = None) -> bool:
        """Verifies target path falls strictly within declared write_scope, resolving symlinks & relative traversals."""
        base_dir = base_dir or Path.cwd()
        try:
            resolved_target = (base_dir / target_path).resolve()
        except Exception:
            return False

        for scope in self.write_scope:
            resolved_scope = (base_dir / scope).resolve()
            try:
                # Check if target is inside or equal to scope directory
                resolved_target.relative_to(resolved_scope)
                return True
            except ValueError:
                continue
        return False


class MeshRegistry:
    def __init__(self, config_path: Path = CONFIG_PATH):
        self.config_path = config_path
        self.nodes: Dict[str, MeshNode] = {}
        self.executor = SovereignPipelineExecutor()
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

    def run_healthcheck(self, node_id: str) -> bool:
        """Executes the healthcheck command for a node. Quarantines node if healthcheck fails."""
        node = self.get_node(node_id)
        if not node:
            return False
        try:
            # Simulate or execute healthcheck in sandbox
            res = subprocess.run(node.healthcheck, shell=True, capture_output=True, text=True, timeout=10.0)
            if res.returncode == 0:
                node.is_quarantined = False
                return True
            else:
                node.is_quarantined = True
                return False
        except Exception:
            node.is_quarantined = True
            return False

    def route_event(self, event_topic: str) -> List[str]:
        """Returns IDs of nodes authorized to receive event_topic."""
        return [node_id for node_id, node in self.nodes.items() if node.can_accept_event(event_topic)]

    def is_event_allowed(self, event_topic: str, source_node_id: str, recipient_node_id: str, effect_path: Optional[str] = None) -> Dict[str, Any]:
        """Evaluates the 6-clause Boolean conjunction:
        allowed = source is registered
              AND source declares event emission
              AND recipient declares event acceptance
              AND source trust tier permits this event class
              AND event effect fits the source write/credential scope
              AND both nodes are healthy and not quarantined
        """
        source = self.get_node(source_node_id)
        if not source:
            return {"allowed": False, "reason": "Clause 1 Failed: Source is not registered"}

        recipient = self.get_node(recipient_node_id)
        if not recipient:
            return {"allowed": False, "reason": "Clause 1 Failed: Recipient is not registered"}

        if not source.can_emit_event(event_topic):
            return {"allowed": False, "reason": f"Clause 2/4 Failed: Source {source_node_id} ({source.trust_tier}) unauthorized to emit {event_topic}"}

        if not recipient.can_accept_event(event_topic):
            return {"allowed": False, "reason": f"Clause 3/6 Failed: Recipient {recipient_node_id} cannot accept {event_topic} (or quarantined)"}

        if effect_path and not source.is_path_in_write_scope(effect_path):
            return {"allowed": False, "reason": f"Clause 5 Failed: Effect path '{effect_path}' outside write scope"}

        if source.is_quarantined or recipient.is_quarantined:
            return {"allowed": False, "reason": "Clause 6 Failed: Source or recipient is quarantined"}

        return {"allowed": True, "source": source_node_id, "recipient": recipient_node_id, "event_topic": event_topic}

    def type_check_and_route(self, event_topic: str, source_node_id: str, payload: Dict[str, Any], effect_path: Optional[str] = None) -> Dict[str, Any]:
        """Type-checks emission permissions, requires attestation for regulated nodes, and routes to accepted recipients."""
        source_node = self.get_node(source_node_id)
        if not source_node:
            return {"status": "denied", "reason": f"Unknown source node: {source_node_id}"}

        if not source_node.can_emit_event(event_topic):
            return {"status": "denied", "reason": f"Node {source_node_id} ({source_node.trust_tier}) unauthorized to emit event {event_topic}"}

        if effect_path and not source_node.is_path_in_write_scope(effect_path):
            return {"status": "denied", "reason": f"Effect path '{effect_path}' outside write scope for node {source_node_id}"}

        # Regulated nodes require attestation
        attestation_hash = None
        if source_node.trust_tier in ["regulated", "core"]:
            attestation_hash = self.executor._attest_event("MESH_EVENT_EMITTED", {
                "source_node": source_node_id,
                "event_topic": event_topic,
                "payload_digest": payload,
            })

        recipients = [nid for nid, node in self.nodes.items() if node.can_accept_event(event_topic)]
        return {
            "status": "routed",
            "source_node": source_node_id,
            "event_topic": event_topic,
            "recipients": recipients,
            "attestation_hash": attestation_hash,
        }

    def execute_non_monetary_provenance_flow(self, initial_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Executes non-monetary provenance flow:
        1. actor-web-automation emits web.result
        2. holixtica-core returns domain.normalized & ledger.entry
        3. holixtica-ledger commits ledger.committed
        4. widow-ui renders committed record (ui.ack)
        5. sweepsync confirms propagation (sync.completed)
        """
        pipeline_steps = [
            ("web.result", "actor-web-automation"),
            ("domain.normalized", "holixtica-core"),
            ("ledger.entry", "holixtica-core"),
            ("ledger.committed", "holixtica-ledger"),
            ("ui.ack", "widow-ui"),
            ("sync.completed", "sweepsync"),
        ]

        history = []
        current_payload = initial_payload
        for event_topic, source_node in pipeline_steps:
            res = self.type_check_and_route(event_topic, source_node, current_payload)
            history.append(res)
            if res["status"] != "routed":
                break
        return history


if __name__ == "__main__":
    registry = MeshRegistry()
    print(f"[MESH REGISTRY] Loaded {len(registry.nodes)} nodes: {list(registry.nodes.keys())}")
    golden_results = registry.execute_golden_path({"query": "sovereign_test"})
    print(f"[MESH REGISTRY] Golden Path Execution ({len(golden_results)} steps):")
    for step in golden_results:
        print(f" - {step['event_topic']} from {step['source_node']} -> {step['recipients']} (Status: {step['status']})")

