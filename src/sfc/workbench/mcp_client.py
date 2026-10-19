"""Minimal stdlib JSON-RPC 2.0 client for an MCP stdio server.

Enough to `initialize`, `tools/list`, and `tools/call` against the Salesforce DX
MCP server (or any MCP stdio server) for the `sfc bench` comparison. Uses the
line-delimited JSON framing of the MCP stdio transport; no third-party deps.
"""

import json
import select
import subprocess
from typing import Dict, List, Optional


class MCPError(Exception):
    pass


class MCPClient:
    def __init__(self, cmd: List[str], cwd: Optional[str] = None, timeout: float = 90.0):
        self.cmd = cmd
        self.cwd = cwd
        self.timeout = timeout
        self.p = None
        self._id = 0

    def __enter__(self):
        self.p = subprocess.Popen(
            self.cmd, cwd=self.cwd,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1,
        )
        self._initialize()
        return self

    def __exit__(self, *exc):
        if not self.p:
            return False
        if self.p.poll() is None:
            try:
                self.p.terminate()
                self.p.wait(timeout=5)
            except Exception:
                try:
                    self.p.kill()
                except Exception:
                    pass
        for stream in (self.p.stdin, self.p.stdout, self.p.stderr):
            try:
                if stream:
                    stream.close()
            except Exception:
                pass
        return False

    def _send(self, obj: Dict):
        self.p.stdin.write(json.dumps(obj) + "\n")
        self.p.stdin.flush()

    def _readline(self) -> str:
        ready, _, _ = select.select([self.p.stdout], [], [], self.timeout)
        if not ready:
            raise MCPError("timeout waiting for MCP response")
        line = self.p.stdout.readline()
        if line == "":
            raise MCPError("MCP server closed its output")
        return line

    def _request(self, method: str, params: Dict) -> Dict:
        self._id += 1
        mid = self._id
        self._send({"jsonrpc": "2.0", "id": mid, "method": method, "params": params})
        while True:
            msg = json.loads(self._readline())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise MCPError(str(msg["error"]))
                return msg.get("result", {})
            # skip notifications / unrelated ids

    def _notify(self, method: str, params: Dict):
        self._send({"jsonrpc": "2.0", "method": method, "params": params})

    def _initialize(self):
        self._request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "sfc-bench", "version": "0.1"},
        })
        self._notify("notifications/initialized", {})

    def list_tools(self) -> List[Dict]:
        return self._request("tools/list", {}).get("tools", [])

    def call_tool(self, name: str, arguments: Dict) -> Dict:
        return self._request("tools/call", {"name": name, "arguments": arguments})


def result_text(result: Dict) -> str:
    """Flatten a tools/call result's content blocks to plain text for sizing."""
    parts = []
    for block in (result.get("content") or []):
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    if not parts:
        return json.dumps(result, separators=(",", ":"))
    return "\n".join(parts)
