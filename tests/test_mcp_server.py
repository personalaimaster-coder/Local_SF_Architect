"""Tests for the sfc MCP stdio server (protocol + tool dispatch)."""

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from sfc import mcp_server  # noqa: E402


class TestMcpProtocol(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        os.chdir(self.root)

    def tearDown(self):
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def test_initialize(self):
        resp = mcp_server._handle(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        self.assertEqual(resp["id"], 1)
        self.assertEqual(resp["result"]["protocolVersion"], mcp_server.PROTOCOL_VERSION)
        self.assertEqual(resp["result"]["serverInfo"]["name"], "sf-compress")

    def test_notification_returns_none(self):
        resp = mcp_server._handle(
            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        self.assertIsNone(resp)

    def test_unknown_method_error(self):
        resp = mcp_server._handle({"jsonrpc": "2.0", "id": 9, "method": "bogus"})
        self.assertEqual(resp["error"]["code"], -32601)

    def test_tools_list_contains_core_tools(self):
        resp = mcp_server._handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        names = {t["name"] for t in resp["result"]["tools"]}
        for expected in ("sfc_setup", "sfc_status", "sfc_run", "sfc_show", "sfc_stats"):
            self.assertIn(expected, names)
        # every tool declares an input schema
        for t in resp["result"]["tools"]:
            self.assertEqual(t["inputSchema"]["type"], "object")

    def test_call_status_on_by_default(self):
        resp = mcp_server._handle({
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "sfc_status", "arguments": {}},
        })
        text = resp["result"]["content"][0]["text"]
        self.assertIn("ACTIVE", text)

    def test_call_unknown_tool_is_error_result(self):
        resp = mcp_server._handle({
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": {"name": "nope", "arguments": {}},
        })
        self.assertTrue(resp["result"]["isError"])

    def test_call_setup_tool(self):
        resp = mcp_server._handle({
            "jsonrpc": "2.0", "id": 5, "method": "tools/call",
            "params": {"name": "sfc_setup", "arguments": {"agent": "agents"}},
        })
        text = resp["result"]["content"][0]["text"]
        summary = json.loads(text)
        self.assertTrue(summary["skills_installed"])
        self.assertTrue(summary["active"])  # sfc is ON by default

    def test_run_requires_command(self):
        resp = mcp_server._handle({
            "jsonrpc": "2.0", "id": 6, "method": "tools/call",
            "params": {"name": "sfc_run", "arguments": {}},
        })
        self.assertTrue(resp["result"]["isError"])

    def test_serve_end_to_end(self):
        # feed initialize + tools/list over the stdio loop
        msgs = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        ]
        stdin = io.StringIO("\n".join(json.dumps(m) for m in msgs) + "\n")
        stdout = io.StringIO()
        mcp_server.serve(stdin=stdin, stdout=stdout)
        lines = [json.loads(x) for x in stdout.getvalue().splitlines() if x.strip()]
        # exactly two responses (the notification produced none)
        self.assertEqual([m["id"] for m in lines], [1, 2])
        self.assertIn("tools", lines[1]["result"])


if __name__ == "__main__":
    unittest.main()
