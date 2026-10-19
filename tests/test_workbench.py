"""Org workbench tests (sfc collect + sfc bench + MCP client), offline via shims."""

import csv
import io
import os
import shlex
import stat
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from sfc import cli  # noqa: E402
from sfc.workbench.mcp_client import MCPClient, result_text  # noqa: E402


def run_cli(*argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        try:
            code = cli.main(list(argv))
        except SystemExit as exc:
            code = exc.code or 0
    return code, buf.getvalue()


# fake `sf` that emits family-shaped output based on its args
FAKE_SF = r'''#!/usr/bin/env python3
import sys, json
a = " ".join(sys.argv[1:])
w = sys.stdout.write
if "retrieve preview" in a or "org list metadata" in a:
    rows = "\n".join("\u2502 Comp%d \u2502 ApexClass \u2502 Add \u2502" % i for i in range(300))
    w("\u250c\u2500\u2500\u252c\u2500\u2500\u252c\u2500\u2500\u2510\n"
      "\u2502 Full Name \u2502 Type \u2502 State \u2502\n"
      "\u251c\u2500\u2500\u253c\u2500\u2500\u253c\u2500\u2500\u2524\n" + rows + "\n"
      "\u2514\u2500\u2500\u2534\u2500\u2500\u2534\u2500\u2500\u2518\n")
elif "data query" in a and "--json" in a:
    recs = [{"attributes": {"type": "Account", "url": "/x/%d" % i},
             "Id": "001%015d" % i, "Name": "Acct%d" % i} for i in range(200)]
    w(json.dumps({"status": 0, "result": {"totalSize": 200, "records": recs}}, indent=2))
elif "sobject describe" in a and "--json" in a:
    fields = [{"name": "F%d__c" % i, "label": "F %d" % i, "type": "string",
               "length": 255, "nillable": True} for i in range(200)]
    w(json.dumps({"status": 0, "result": {"name": "Account", "fields": fields}}, indent=2))
elif "apex run test" in a:
    body = "\n".join("MyTest.m%d  Pass  30ms" % i for i in range(100))
    w("=== Test Summary\nOutcome  Passed\nPass Rate  99%\nFail Rate  1%\n" + body +
      "\nBadTest.t  Fail  System.AssertException\n")
elif "project deploy validate" in a:
    rows = "\n".join("Component C%d  ApexClass  Succeeded" % i for i in range(100))
    w("=== Deploy Validate\nStatus: Succeeded\nComponents: 100\n" + rows + "\n")
else:
    w("unknown\n")
'''

# fake MCP stdio server: line-delimited JSON-RPC, one tool "run_soql_query"
FAKE_MCP = r'''#!/usr/bin/env python3
import sys, json
def send(o): sys.stdout.write(json.dumps(o) + "\n"); sys.stdout.flush()
for line in sys.stdin:
    line = line.strip()
    if not line: continue
    msg = json.loads(line)
    mid = msg.get("id"); method = msg.get("method")
    if method == "initialize":
        send({"jsonrpc": "2.0", "id": mid, "result": {
            "protocolVersion": "2024-11-05", "serverInfo": {"name": "fake", "version": "1"},
            "capabilities": {}}})
    elif method == "notifications/initialized":
        pass
    elif method == "tools/list":
        send({"jsonrpc": "2.0", "id": mid, "result": {"tools": [
            {"name": "run_soql_query", "description": "Run a SOQL query against the org"}]}})
    elif method == "tools/call":
        send({"jsonrpc": "2.0", "id": mid, "result": {"content": [
            {"type": "text", "text": "Id,Name\n001,Acct0\n002,Acct1\n"}]}})
    elif mid is not None:
        send({"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "no"}})
'''


def _write_exe(path, body):
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


class _Base(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)
        self._binp = Path(self._tmp.name) / "bin"
        self._binp.mkdir()
        _write_exe(self._binp / "sf", FAKE_SF)
        self._mcp = Path(self._tmp.name) / "fake_mcp.py"
        self._mcp.write_text(FAKE_MCP)
        self._old_path = os.environ["PATH"]
        os.environ["PATH"] = str(self._binp) + os.pathsep + self._old_path

    def tearDown(self):
        os.environ["PATH"] = self._old_path
        os.chdir(self._cwd)
        self._tmp.cleanup()


class TestCollect(_Base):
    def _index(self, out="collected"):
        with open(Path(out) / "index.csv") as fh:
            return {r["name"]: r for r in csv.DictReader(fh)}

    def test_readonly_skips_org_writes(self):
        code, out = run_cli("collect")
        self.assertEqual(code, 0)
        idx = self._index()
        # read-only families captured
        self.assertTrue(Path("collected/retrieve-preview.txt").exists())
        self.assertTrue(Path("collected/data-query-json.txt").exists())
        self.assertTrue(Path("collected/retrieve-preview.txt").read_text().startswith("$ sf "))
        self.assertEqual(idx["retrieve-preview"]["ran"], "True")
        self.assertGreater(float(idx["retrieve-preview"]["reduction_pct"]), 90.0)
        self.assertGreater(float(idx["data-query-json"]["reduction_pct"]), 50.0)
        # org-write steps skipped
        self.assertEqual(idx["apex-run-test"]["ran"], "False")
        self.assertEqual(idx["deploy-validate"]["ran"], "False")
        self.assertFalse(Path("collected/apex-run-test.txt").exists())

    def test_allow_org_writes_runs_all(self):
        code, out = run_cli("collect", "--allow-org-writes")
        self.assertEqual(code, 0)
        idx = self._index()
        self.assertEqual(idx["apex-run-test"]["ran"], "True")
        self.assertEqual(idx["deploy-validate"]["ran"], "True")
        self.assertTrue(Path("collected/apex-run-test.txt").exists())
        self.assertIn("=== Test Summary",
                      Path("collected/apex-run-test.txt").read_text())


class TestMCPClient(_Base):
    def test_initialize_list_call(self):
        with MCPClient([sys.executable, str(self._mcp)]) as client:
            tools = client.list_tools()
            self.assertEqual(tools[0]["name"], "run_soql_query")
            res = client.call_tool("run_soql_query", {"query": "SELECT Id FROM Account"})
            self.assertIn("Acct0", result_text(res))


class TestBench(_Base):
    def test_bench_report_generated(self):
        code, out = run_cli("bench", "--mcp-cmd",
                            "{} {}".format(shlex.quote(sys.executable),
                                           shlex.quote(str(self._mcp))))
        self.assertEqual(code, 0)
        report = Path("bench-report.md").read_text()
        self.assertIn("CLI raw", report)
        self.assertIn("run_soql_query", report)         # discovered MCP tool
        self.assertIn("| query |", report)              # query row present
        # CLI side measured a large raw payload for query
        self.assertIn("Discovered MCP tools", report)

    def test_bench_without_mcp_still_reports_cli(self):
        code, out = run_cli("bench", "--mcp-cmd", "definitely-not-a-real-binary-xyz")
        self.assertEqual(code, 0)
        report = Path("bench-report.md").read_text()
        self.assertIn("MCP side unavailable", report)
        self.assertIn("| query |", report)


if __name__ == "__main__":
    unittest.main()
