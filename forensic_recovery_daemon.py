#!/usr/bin/env python3
"""
AgentK forensic recovery daemon.

Read-only by default. Reconstructs repository state from Git history, maps
Python imports and local service endpoints, and reports missing dependencies.
Optional repair restores only missing tracked files from HEAD; it never
overwrites an existing file or edits source configuration.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXCLUDED = {".git", ".venv", "venv", "__pycache__", "node_modules", ".pytest_cache"}
SOURCE_SUFFIXES = {".py", ".sh", ".yml", ".yaml", ".toml", ".json"}
SENSITIVE_NAME = re.compile(r"(?:^|_)(?:SECRET|TOKEN|PASSWORD|API_KEY|PRIVATE_KEY)(?:$|_)", re.I)
URL_PATTERN = re.compile(r"https?://(?:localhost|127\\.0\\.0\\.1|0\\.0\\.0\\.0|[a-zA-Z0-9._-]+)(?::\\d+)?(?:/[^\\s\"'<>]*)?")


def git(root: Path, *args: str) -> str:
    p = subprocess.run(["git", "-C", str(root), *args], text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    if p.returncode:
        return ""
    return p.stdout.strip()


def tracked_paths(root: Path) -> set[str]:
    return set(filter(None, git(root, "ls-files").splitlines()))


def iter_source_files(root: Path):
    for p in root.rglob("*"):
        if not p.is_file() or any(part in EXCLUDED for part in p.relative_to(root).parts):
            continue
        if p.suffix.lower() in SOURCE_SUFFIXES and ".env" not in p.name:
            yield p


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def history_deleted_files(root: Path, limit: int) -> list[dict[str, str]]:
    raw = git(root, "log", "--all", f"-n{limit}", "--date=short",
              "--format=COMMIT%x09%H%x09%ad", "--name-status", "--diff-filter=D")
    deleted: list[dict[str, str]] = []
    current_commit = ""
    current_date = ""
    for line in raw.splitlines():
        if line.startswith("COMMIT\t"):
            _, current_commit, current_date = line.split("\t", 2)
        elif line.startswith("D\t"):
            deleted.append({"path": line[2:], "commit": current_commit, "date": current_date})
    return deleted


def module_inventory(root: Path) -> tuple[set[str], list[dict[str, str]]]:
    modules: set[str] = set()
    imports: list[dict[str, str]] = []
    for path in iter_source_files(root):
        if path.suffix != ".py":
            continue
        rel = path.relative_to(root)
        module = ".".join(rel.with_suffix("").parts)
        if module.endswith(".__init__"):
            module = module[:-9]
        modules.add(module)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError, OSError) as e:
            imports.append({"file": str(rel), "kind": "parse_error", "target": str(e)})
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({"file": str(rel), "kind": "import", "target": alias.name})
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append({"file": str(rel), "kind": "from", "target": node.module})
    return modules, imports


def audit(root: Path, history_limit: int) -> dict[str, Any]:
    tracked = tracked_paths(root)
    modules, imports = module_inventory(root)
    missing_imports = []
    top_level = {m.split(".")[0] for m in modules}
    for item in imports:
        target = item["target"]
        head = target.split(".")[0]
        if head in {"agents", "tools"} and head not in top_level:
            missing_imports.append(item)
        elif target.startswith("agents.") or target.startswith("tools."):
            if target not in modules and not any(m.startswith(target + ".") for m in modules):
                missing_imports.append(item)

    source_text: dict[str, str] = {}
    urls: list[dict[str, str]] = []
    env_refs: set[str] = set()
    for path in iter_source_files(root):
        try:
            body = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = str(path.relative_to(root))
        source_text[rel] = body
        urls.extend({"file": rel, "url": u} for u in URL_PATTERN.findall(body))
        env_refs.update(re.findall(r"os\\.getenv\\(\\s*[\"']([A-Z0-9_]+)", body))

    flat = "\n".join(source_text.values())
    deleted = history_deleted_files(root, history_limit)
    deleted_now_missing = sorted({d["path"] for d in deleted if d["path"] not in tracked and not (root / d["path"]).exists()})
    refs = {
        "hermes_kernel": "agents/hermes.py" in tracked,
        "sdk_bootstrap": "agent_kernel.py" in tracked,
        "sdk_bridge": "agents/sdk_bridge.py" in tracked,
        "sovereign_gate": "agents/sovereign_gate.py" in tracked,
        "self_heal_script": "self_heal.sh" in tracked,
        "a2a_protocol_repository": False,
        "ollama_configured": "OLLAMA_API_BASE" in flat or "localhost:11434" in flat,
        "qwen36_named_in_source": bool(re.search(r"qwen\\s*3[._-]?6|qwen3\\.6", flat, re.I)),
        "gcp_project_id_reference": bool(re.search(r"GOOGLE_CLOUD_PROJECT|GCLOUD_PROJECT|project_id\\s*=", flat)),
        "gcp_deploy_step_reference": bool(re.search(r"gcloud\\s+(run|build|deploy)|google-github-actions/auth|workload_identity_provider", flat)),
        "github_actions_workflow": any(p.startswith(".github/workflows/") for p in tracked),
        "dispatch_agent_defined": "def dispatch_agent" in flat,
        "dispatch_agent_registered_in_bootstrap": bool(re.search(r"(?:tools|capabilities|toolset).*dispatch_agent", flat, re.I | re.S)),
    }
    current_files = {}
    for rel in ("agent_kernel.py", "agents/hermes.py", "agents/sdk_bridge.py",
                "agents/sovereign_gate.py", "config.py", "self_heal.sh",
                ".github/workflows/ci.yml"):
        p = root / rel
        if p.is_file():
            current_files[rel] = {"sha256": sha256(p), "bytes": p.stat().st_size}

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "git": {
            "head": git(root, "rev-parse", "HEAD"),
            "branch": git(root, "branch", "--show-current"),
            "status": git(root, "status", "--short"),
            "branches": git(root, "branch", "--format=%(refname:short)").splitlines(),
            "tags": git(root, "tag", "--list").splitlines(),
            "recent_commits": git(root, "log", "-n20", "--format=%H%x09%ad%x09%s", "--date=short").splitlines(),
        },
        "root_presence": refs,
        "tracked_file_count": len(tracked),
        "python_module_count": len(modules),
        "missing_internal_imports": missing_imports,
        "historically_deleted_paths": deleted_now_missing,
        "deletion_evidence": deleted[:200],
        "local_and_external_endpoints": urls,
        "environment_variable_names": sorted(env_refs),
        "root_file_hashes": current_files,
        "safety": {
            "read_only_default": True,
            "repair_scope": "restore missing tracked paths from HEAD only; never overwrite existing files",
            "secrets_values_collected": False,
        },
    }


def restore_missing_from_head(root: Path, report: dict[str, Any]) -> list[str]:
    restored = []
    tracked = tracked_paths(root)
    for rel in report["historically_deleted_paths"]:
        if rel not in tracked or (root / rel).exists():
            continue
        p = subprocess.run(["git", "-C", str(root), "restore", "--source=HEAD", "--worktree", "--", rel],
                           text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        if p.returncode == 0 and (root / rel).is_file():
            restored.append(rel)
    return restored


def main() -> int:
    parser = argparse.ArgumentParser(description="AgentK forensic recovery watchdog")
    parser.add_argument("--root", default=os.environ.get("AGENTK_ROOT", str(Path(__file__).resolve().parent)))
    parser.add_argument("--output", default="")
    parser.add_argument("--history-limit", type=int, default=500)
    parser.add_argument("--restore-missing", action="store_true",
                        help="restore only files deleted from the working tree but present in HEAD")
    parser.add_argument("--watch", action="store_true", help="repeat read-only audits")
    parser.add_argument("--interval", type=int, default=60)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not (root / ".git").exists():
        print(f"ERROR: {root} is not a Git working tree.", file=sys.stderr)
        return 2

    while True:
        report = audit(root, max(1, args.history_limit))
        if args.restore_missing:
            report["restored_missing_files"] = restore_missing_from_head(root, report)
            report["post_restore_git_status"] = git(root, "status", "--short")
        payload = json.dumps(report, indent=2, sort_keys=True)
        if args.output:
            out = Path(args.output).expanduser().resolve()
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(payload + "\n", encoding="utf-8")
        print(payload, flush=True)
        if not args.watch:
            break
        time.sleep(max(5, args.interval))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
