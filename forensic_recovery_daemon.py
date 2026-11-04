#!/usr/bin/env python3
"""
AgentK forensic recovery watchdog.

Read-only by default. Reconstructs repository state from Git history, maps
Python imports and service endpoints, and reports missing dependencies.
Optional repair restores only tracked files missing from the working tree.
It never overwrites an existing file or edits source configuration.
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
URL_PATTERN = re.compile(r"https?://(?:localhost|127\.0\.0\.1|0\.0\.0\.0|[a-zA-Z0-9._-]+)(?::\d+)?(?:/[^\s\"'<>]*)?")


def git(root: Path, *args: str) -> str:
    p = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30
    )
    return p.stdout.strip() if p.returncode == 0 else ""


def tracked_paths(root: Path) -> set[str]:
    return set(filter(None, git(root, "ls-files").splitlines()))


def iter_source_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file() or any(part in EXCLUDED for part in path.relative_to(root).parts):
            continue
        if path.suffix.lower() in SOURCE_SUFFIXES and ".env" not in path.name:
            yield path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def history_deleted_files(root: Path, limit: int) -> list[dict[str, str]]:
    raw = git(
        root, "log", "--all", f"-n{limit}", "--date=short",
        "--format=COMMIT%x09%H%x09%ad", "--name-status", "--diff-filter=D"
    )
    deleted: list[dict[str, str]] = []
    commit = ""
    date = ""
    for line in raw.splitlines():
        if line.startswith("COMMIT\t"):
            _, commit, date = line.split("\t", 2)
        elif line.startswith("D\t"):
            deleted.append({"path": line[2:], "commit": commit, "date": date})
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
        except (SyntaxError, UnicodeDecodeError, OSError) as error:
            imports.append({"file": str(rel), "kind": "parse_error", "target": str(error)})
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
    top_level = {module.split(".")[0] for module in modules}
    for item in imports:
        target = item["target"]
        head = target.split(".")[0]
        if head in {"agents", "tools"} and head not in top_level:
            missing_imports.append(item)
        elif target.startswith(("agents.", "tools.")):
            if target not in modules and not any(m.startswith(target + ".") for m in modules):
                missing_imports.append(item)

    source_text: dict[str, str] = {}
    endpoints: list[dict[str, str]] = []
    env_refs: set[str] = set()
    for path in iter_source_files(root):
        try:
            body = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = str(path.relative_to(root))
        source_text[rel] = body
        for url in URL_PATTERN.findall(body):
            endpoints.append({"file": rel, "url": url.split("?", 1)[0]})
        env_refs.update(re.findall(r"os\.getenv\(\s*['\"]([A-Z0-9_]+)", body))

    flat = "\n".join(source_text.values())
    deleted = history_deleted_files(root, history_limit)
    head_sha = git(root, "rev-parse", "HEAD")
    missing_from_worktree = sorted(filter(None, git(root, "ls-files", "--deleted").splitlines()))
    deleted_from_current_head = set()
    for item in deleted:
        if head_sha and subprocess.run(
            ["git", "-C", str(root), "cat-file", "-e", f"{head_sha}:{item['path']}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ).returncode != 0:
            deleted_from_current_head.add(item["path"])

    bootstrap = source_text.get("agent_kernel.py", "")
    bridge = source_text.get("agents/sdk_bridge.py", "")
    refs = {
        "hermes_kernel": "agents/hermes.py" in tracked,
        "sdk_bootstrap": "agent_kernel.py" in tracked,
        "sdk_bridge": "agents/sdk_bridge.py" in tracked,
        "sovereign_gate": "agents/sovereign_gate.py" in tracked,
        "self_heal_script": "self_heal.sh" in tracked,
        "ollama_endpoint_configured_in_source": "OLLAMA_API_BASE" in flat or "localhost:11434" in flat,
        "qwen36_named_in_source": bool(re.search(r"qwen\s*3[._-]?6|qwen3\.6", flat, re.I)),
        "gcp_project_id_reference": bool(re.search(r"GOOGLE_CLOUD_PROJECT|GCLOUD_PROJECT|project_id\s*=", flat)),
        "gcp_deploy_step_reference": bool(re.search(
            r"gcloud\s+(run|build|deploy)|google-github-actions/auth|workload_identity_provider",
            flat, re.I
        )),
        "github_actions_workflow": any(path.startswith(".github/workflows/") for path in tracked),
        "dispatch_agent_defined_in_bridge": "def dispatch_agent" in bridge,
        "dispatch_agent_referenced_in_bootstrap": "dispatch_agent" in bootstrap,
    }

    root_hashes = {}
    for rel in ("agent_kernel.py", "agents/hermes.py", "agents/sdk_bridge.py",
                "agents/sovereign_gate.py", "config.py", "self_heal.sh",
                ".github/workflows/ci.yml"):
        path = root / rel
        if path.is_file():
            root_hashes[rel] = {"sha256": sha256(path), "bytes": path.stat().st_size}

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "git": {
            "head": head_sha,
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
        "missing_from_working_tree": missing_from_worktree,
        "historically_deleted_from_current_head": sorted(deleted_from_current_head),
        "deletion_evidence": deleted[:200],
        "local_and_external_endpoints": endpoints,
        "environment_variable_names": sorted(env_refs),
        "root_file_hashes": root_hashes,
        "safety": {
            "read_only_default": True,
            "repair_scope": "restore tracked files missing from the working tree from HEAD only",
            "never_overwrites_existing_files": True,
            "secret_values_collected": False,
        },
    }


def restore_missing_from_head(root: Path, report: dict[str, Any]) -> list[str]:
    restored = []
    tracked = tracked_paths(root)
    for rel in report["missing_from_working_tree"]:
        if rel not in tracked or (root / rel).exists():
            continue
        result = subprocess.run(
            ["git", "-C", str(root), "restore", "--source=HEAD", "--worktree", "--", rel],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30
        )
        if result.returncode == 0 and (root / rel).is_file():
            restored.append(rel)
    return restored


def main() -> int:
    parser = argparse.ArgumentParser(description="AgentK forensic recovery watchdog")
    parser.add_argument("--root", default=os.environ.get("AGENTK_ROOT", str(Path(__file__).resolve().parent)))
    parser.add_argument("--output", default="")
    parser.add_argument("--history-limit", type=int, default=500)
    parser.add_argument("--restore-missing", action="store_true",
                        help="restore tracked files missing from the working tree; never overwrite")
    parser.add_argument("--watch", action="store_true", help="repeat read-only audits")
    parser.add_argument("--interval", type=int, default=60)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if git(root, "rev-parse", "--is-inside-work-tree") != "true":
        print(f"ERROR: {root} is not a Git working tree.", file=sys.stderr)
        return 2

    while True:
        report = audit(root, max(1, args.history_limit))
        if args.restore_missing:
            report["restored_missing_files"] = restore_missing_from_head(root, report)
            report["post_restore_git_status"] = git(root, "status", "--short")
        payload = json.dumps(report, indent=2, sort_keys=True)
        if args.output:
            output = Path(args.output).expanduser().resolve()
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(payload + "\n", encoding="utf-8")
        print(payload, flush=True)
        if not args.watch:
            break
        time.sleep(max(5, args.interval))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
