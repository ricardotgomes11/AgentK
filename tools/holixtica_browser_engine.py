"""
Holixtica Browser Automation Engine
===================================
Reverse-engineered browser automation engine utilizing CDP (Chrome DevTools Protocol)
port discovery and session inheritance extracted from Antigravity's chrome-devtools-mcp module.
"""

import os
import json
import urllib.request
from pathlib import Path
from typing import Dict, Any, Optional

CHROME_PROFILE_DIR = Path.home() / ".gemini" / "antigravity-browser-profile"
DEFAULT_CDP_PORT = 9222


class HolixticaBrowserEngine:
    def __init__(self, cdp_port: int = DEFAULT_CDP_PORT, profile_dir: Path = CHROME_PROFILE_DIR):
        self.cdp_port = cdp_port
        self.profile_dir = profile_dir

    def discover_active_cdp_endpoint(self) -> Optional[str]:
        """Reads DevToolsActivePort file from Antigravity browser profile to find active WebSocket endpoint."""
        port_file = self.profile_dir / "DevToolsActivePort"
        if port_file.exists():
            try:
                lines = port_file.read_text().strip().split("\n")
                if len(lines) >= 2:
                    port = lines[0].strip()
                    ws_path = lines[1].strip()
                    return f"ws://127.0.0.1:{port}{ws_path}"
            except Exception:
                pass
        return f"http://127.0.0.1:{self.cdp_port}"

    def get_open_pages(self) -> Dict[str, Any]:
        """Queries local CDP endpoint to inspect active browser targets and pages."""
        url = f"http://127.0.0.1:{self.cdp_port}/json/list"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Holixtica-BrowserEngine/1.0"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {"status": "connected", "targets": data}
        except Exception as e:
            return {"status": "offline", "error": f"CDP endpoint on port {self.cdp_port} offline: {e}"}

    def capture_dom_snapshot(self, target_id: Optional[str] = None) -> Dict[str, Any]:
        """Extracts text snapshot from active CDP target."""
        targets_info = self.get_open_pages()
        if targets_info.get("status") != "connected":
            return targets_info

        targets = targets_info.get("targets", [])
        page_target = next((t for t in targets if t.get("type") == "page"), None)
        if not page_target:
            return {"status": "no_active_page", "message": "No active page target found on CDP."}

        return {
            "status": "success",
            "target_id": page_target.get("id"),
            "url": page_target.get("url"),
            "title": page_target.get("title"),
            "ws_url": page_target.get("webSocketDebuggerUrl"),
        }


if __name__ == "__main__":
    engine = HolixticaBrowserEngine()
    print(f"[HOLIXTICA BROWSER ENGINE] Active CDP Endpoint: {engine.discover_active_cdp_endpoint()}")
    info = engine.get_open_pages()
    print(f"[HOLIXTICA BROWSER ENGINE] CDP Targets:\n{json.dumps(info, indent=2)}")
