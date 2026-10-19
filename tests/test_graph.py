"""graphify-sf adapter tests: gating (active + toggle), forwarding, metering.

Uses a fake `graphify-sf` shim on PATH so no real install / network is needed.
"""

import io
import json
import os
import stat
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from sfc import cli, metering  # noqa: E402


def run_cli(*argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        try:
            code = cli.main(list(argv))
        except SystemExit as exc:
            code = exc.code or 0
    return code, buf.getvalue()


SHIM = """#!/bin/sh
if [ "$1" = "--version" ]; then echo "graphify-sf v0.4.1"; exit 0; fi
echo "ARGS: $@"
exit 0
"""


class _Base(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)
        self._binp = Path(self._tmp.name) / "bin"
        self._binp.mkdir()
        self._old_path = os.environ["PATH"]

    def tearDown(self):
        os.environ["PATH"] = self._old_path
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def _install_shim(self):
        shim = self._binp / "graphify-sf"
        shim.write_text(SHIM)
        shim.chmod(shim.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    def _isolate_path(self, with_shim):
        if with_shim:
            self._install_shim()
        # PATH with only our bin dir => no real graphify-sf/uvx/pipx leaks in
        os.environ["PATH"] = str(self._binp)

    def _enable_graph(self):
        cfg_path = Path(".sfc") / "config.json"
        cfg = json.loads(cfg_path.read_text())
        cfg["exploration-graph"] = True
        cfg_path.write_text(json.dumps(cfg))


class TestGraphGating(_Base):
    def test_inactive_refuses(self):
        run_cli("off")  # sfc is ON by default; opt out to exercise the inactive path
        self._isolate_path(with_shim=True)
        code, out = run_cli("graph", "query", "anything")
        self.assertEqual(code, 3)
        self.assertIn("inactive", out)

    def test_active_but_toggle_off(self):
        run_cli("on")
        self._isolate_path(with_shim=True)
        code, out = run_cli("graph", "query", "anything")
        self.assertEqual(code, 4)
        self.assertIn("exploration-graph is OFF", out)

    def test_active_toggle_on_but_not_installed(self):
        run_cli("on")
        self._enable_graph()
        self._isolate_path(with_shim=False)   # no graphify-sf on PATH
        code, out = run_cli("graph", "query", "anything")
        self.assertEqual(code, 5)
        self.assertIn("graphify-sf not found", out)
        self.assertIn("pipx install graphify-sf==0.4.1", out)


class TestGraphForwarding(_Base):
    def test_query_forwards_and_injects_budget_and_meters(self):
        run_cli("on")
        self._enable_graph()
        self._isolate_path(with_shim=True)
        code, out = run_cli("graph", "query", "where is Foo used?")
        self.assertEqual(code, 0)
        self.assertIn("ARGS: query where is Foo used? --budget 2000", out)
        rows = [r for r in metering.read_rows() if r["family"] == "graph"]
        self.assertEqual(len(rows), 1)

    def test_budget_not_double_injected(self):
        run_cli("on")
        self._enable_graph()
        self._isolate_path(with_shim=True)
        code, out = run_cli("graph", "query", "q", "--budget", "500")
        self.assertEqual(code, 0)
        self.assertIn("ARGS: query q --budget 500", out)
        self.assertNotIn("2000", out)

    def test_non_query_passthrough(self):
        run_cli("on")
        self._enable_graph()
        self._isolate_path(with_shim=True)
        code, out = run_cli("graph", "stats")
        self.assertEqual(code, 0)
        self.assertIn("ARGS: stats", out)
        self.assertNotIn("--budget", out)


if __name__ == "__main__":
    unittest.main()
