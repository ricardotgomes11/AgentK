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
import signal
import sqlite3
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


MAX_CYCLES = 1000
SHUTDOWN_SIGNAL: int | None = None


def _request_shutdown(signum: int, _frame: Any) -> None:
    global SHUTDOWN_SIGNAL
    SHUTDOWN_SIGNAL = signum


def _canonical_payload(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _ledger_insert(
    conn: sqlite3.Connection, cycle_index: int, origin: str,
    state: str, payload_data: dict[str, Any]
) -> str:
    payload_str = _canonical_payload(payload_data)
    checksum = hashlib.sha256(
        f"{cycle_index}:{origin}:{state}:{payload_str}".encode("utf-8")
    ).hexdigest()
    conn.execute(
        """
        INSERT INTO sovereign_ledger (cycle_index, origin, state, checksum, payload)
        VALUES (?, ?, ?, ?, ?)
        """,
        (cycle_index, origin, state, checksum, payload_str),
    )
    conn.commit()
    return checksum


def verify_ledger(conn: sqlite3.Connection) -> dict[str, Any]:
    checked = 0
    for cycle_index, origin, state, checksum, payload in conn.execute(
        "SELECT cycle_index, origin, state, checksum, payload "
        "FROM sovereign_ledger ORDER BY cycle_index"
    ):
        expected = hashlib.sha256(
            f"{cycle_index}:{origin}:{state}:{payload}".encode("utf-8")
        ).hexdigest()
        if not hashlib.compare_digest(checksum, expected):
            raise RuntimeError(f"Ledger checksum mismatch at cycle {cycle_index}")
        # Require canonical JSON, so alternate encodings cannot represent the same state.
        parsed = json.loads(payload)
        if _canonical_payload(parsed) != payload:
            raise RuntimeError(f"Non-canonical ledger payload at cycle {cycle_index}")
        checked += 1
    return {"verified_records": checked, "integrity": "VALID"}


def main() -> int:
    parser = argparse.ArgumentParser(description="AgentK forensic recovery watchdog")
    parser.add_argument("--root", default=os.environ.get("AGENTK_ROOT", str(Path(__file__).resolve().parent)))
    parser.add_argument("--output", default="")
    parser.add_argument("--history-limit", type=int, default=500)
    parser.add_argument("--restore-missing", action="store_true",
                        help="restore tracked files missing from the working tree; never overwrite")
    parser.add_argument("--watch", action="store_true", help="repeat read-only audits")
    parser.add_argument("--interval", type=int, default=60)
    parser.add_argument("--max-cycles", type=int, default=MAX_CYCLES,
                        help="maximum ACTIVE cycles before the terminal ledger record")
    parser.add_argument(
        "--ledger",
        default=os.environ.get(
            "AGENTK_LEDGER_PATH",
            str(Path.home() / ".agentk" / "sovereign_ledger.sqlite3"),
        ),
        help="SQLite ledger path (defaults outside the repository)",
    )
    args = parser.parse_args()
    if args.max_cycles < 1:
        parser.error("--max-cycles must be at least 1")
    if args.interval < 1:
        parser.error("--interval must be at least 1")

    root = Path(args.root).resolve()
    if git(root, "rev-parse", "--is-inside-work-tree") != "true":
        print(f"ERROR: {root} is not a Git working tree.", file=sys.stderr)
        return 2

    ledger_path = Path(args.ledger).expanduser().resolve()
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(ledger_path), timeout=30)
    conn.execute("PRAGMA synchronous=FULL")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sovereign_ledger (
            cycle_index INTEGER PRIMARY KEY,
            origin TEXT NOT NULL,
            state TEXT NOT NULL,
            checksum TEXT NOT NULL,
            payload TEXT NOT NULL
        )
    """)
    conn.commit()

    try:
        integrity = verify_ledger(conn)
        existing = conn.execute(
            "SELECT COUNT(*) FROM sovereign_ledger"
        ).fetchone()[0]
        if existing:
            raise RuntimeError(
                f"Ledger already contains {existing} records; refusing to append "
                "a new cycle sequence to the existing primary-key space. "
                "Choose a new --ledger path to start a separate run."
            )

        global SHUTDOWN_SIGNAL
        SHUTDOWN_SIGNAL = None
        signal.signal(signal.SIGINT, _request_shutdown)
        signal.signal(signal.SIGTERM, _request_shutdown)

        cycle = 1
        while True:
            if SHUTDOWN_SIGNAL is not None:
                signal_name = signal.Signals(SHUTDOWN_SIGNAL).name
                payload_data = {
                    "status": "HALTED_SIGNAL",
                    "final_cycle": cycle - 1,
                    "signal": signal_name,
                }
                terminal_hash = _ledger_insert(
                    conn, cycle, "system_manager", "HALTED_SIGNAL", payload_data
                )
                print(
                    f"[SHUTDOWN] {signal_name}; ledger terminal record "
                    f"cycle={cycle}, sha256={terminal_hash}",
                    flush=True,
                )
                break

            if cycle > args.max_cycles:
                payload_data = {
                    "status": "MAX_CYCLES_REACHED",
                    "final_cycle": cycle - 1,
                }
                terminal_hash = _ledger_insert(
                    conn, cycle, "system_manager",
                    "HALTED_DETERMINISTIC", payload_data
                )
                print(
                    f"[LIMIT] Maximum cycles reached ({args.max_cycles}). "
                    f"State locked: HALTED_DETERMINISTIC; "
                    f"terminal cycle={cycle}; sha256={terminal_hash}",
                    flush=True,
                )
                break

            report = audit(root, max(1, args.history_limit))
            if args.restore_missing:
                report["restored_missing_files"] = restore_missing_from_head(root, report)
                report["post_restore_git_status"] = git(root, "status", "--short")

            payload_data = {
                "cycle": cycle,
                "status": "ACTIVE",
                "audit": report,
            }
            state_hash = _ledger_insert(
                conn, cycle, "stream_worker", "CYCLING", payload_data
            )

            if args.output:
                output = Path(args.output).expanduser().resolve()
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(
                    json.dumps(
                        {
                            "cycle": cycle,
                            "state": "CYCLING",
                            "checksum": state_hash,
                            "ledger": str(ledger_path),
                            "audit": report,
                        },
                        indent=2,
                        sort_keys=True,
                    ) + "\n",
                    encoding="utf-8",
                )
            print(
                json.dumps(
                    {"cycle": cycle, "state": "CYCLING", "checksum": state_hash},
                    sort_keys=True,
                ),
                flush=True,
            )
            cycle += 1
            if not args.watch:
                break
            if cycle <= args.max_cycles and SHUTDOWN_SIGNAL is None:
                time.sleep(max(1, args.interval))

        verification = verify_ledger(conn)
        final_row = conn.execute(
            "SELECT cycle_index, state, checksum FROM sovereign_ledger "
            "ORDER BY cycle_index DESC LIMIT 1"
        ).fetchone()
        print(
            json.dumps(
                {
                    "ledger": str(ledger_path),
                    "verification": verification,
                    "terminal_record": {
                        "cycle_index": final_row[0],
                        "state": final_row[1],
                        "checksum": final_row[2],
                    },
                },
                sort_keys=True,
            ),
            flush=True,
        )
        return 0
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 3
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
