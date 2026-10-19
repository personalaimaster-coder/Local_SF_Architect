"""Deploy-retry delta tests: unit (compute/render/find_prev) + integration."""

import io
import os
import stat
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from sfc import cli, delta, metering, state, store  # noqa: E402


def run_cli(*argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        try:
            code = cli.main(list(argv))
        except SystemExit as exc:
            code = exc.code or 0
    return code, buf.getvalue()


DEPLOY_SHIM = """#!/bin/sh
n=0
if [ -f "$SF_SHIM_COUNTER" ]; then n=$(cat "$SF_SHIM_COUNTER"); fi
n=$((n+1))
echo "$n" > "$SF_SHIM_COUNTER"
echo "=== Deploy Validate"
echo "Status: Failed"
echo "Deploy ID: 0Af0000000000${n}AAA"
i=1
while [ "$i" -le 50 ]; do echo "Component C${i}  ApexClass  Succeeded"; i=$((i+1)); done
if [ "$n" -eq 1 ]; then
  echo "Error  classes/A.cls  Missing ';' (line 3)"
else
  echo "Error  classes/B.cls  Undefined variable x (line 9)"
fi
exit 0
"""


class TestDeltaUnit(unittest.TestCase):
    def test_extract_errors_excludes_status(self):
        text = ("=== Deploy Validate\nStatus: Failed\nDeploy ID: 0Af1\n"
                "Components: 5\nError classes/A.cls bad\n0 errors found\n")
        errs = delta.extract_errors(text)
        self.assertEqual(errs, ["Error classes/A.cls bad"])

    def test_compute_new_resolved_unchanged(self):
        prev = "Error A\nError B\n"
        curr = "Error B\nError C\n"
        new, resolved, unchanged = delta.compute(prev, curr)
        self.assertEqual(new, ["Error C"])
        self.assertEqual(resolved, ["Error A"])
        self.assertEqual(unchanged, ["Error B"])

    def test_render_points_to_previous(self):
        out = delta.render("PREV1", "Status: Failed", ["Error C"], ["Error A"], ["Error B"])
        self.assertIn("[sfc delta] vs run PREV1", out)
        self.assertIn("1 new, 1 resolved, 1 unchanged", out)
        self.assertIn("Error C", out)
        self.assertIn("sfc show PREV1", out)
        self.assertIn("Status: Failed", out)


class TestFindPrev(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)
        Path(".sfc").mkdir()

    def tearDown(self):
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def test_find_prev_matches_normalized_command(self):
        store.save("id-old", "sf project deploy start", "old body\nError X", 50)
        store.save("id-new", "sf   project deploy   start", "new body\nError Y", 50)
        found = store.find_prev("sf project deploy start", "id-new")
        self.assertIsNotNone(found)
        self.assertEqual(found[0], "id-old")
        self.assertIn("Error X", found[1])
        # no match for a different command
        self.assertIsNone(store.find_prev("sf apex run test", "id-new"))


class TestDeltaIntegration(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)
        binp = Path(self._tmp.name) / "bin"
        binp.mkdir()
        shim = binp / "sf"
        shim.write_text(DEPLOY_SHIM)
        shim.chmod(shim.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        self._old_path = os.environ["PATH"]
        os.environ["PATH"] = str(binp) + os.pathsep + self._old_path
        os.environ["SF_SHIM_COUNTER"] = str(Path(self._tmp.name) / "counter")

    def tearDown(self):
        os.environ["PATH"] = self._old_path
        os.environ.pop("SF_SHIM_COUNTER", None)
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def test_second_run_emits_delta(self):
        run_cli("on")
        code, out1 = run_cli("run", "--", "sf", "project", "deploy", "start")
        self.assertEqual(code, 0)
        self.assertNotIn("[sfc delta]", out1)          # first run: normal report
        self.assertIn("component/row(s) Succeeded", out1)

        code, out2 = run_cli("run", "--", "sf", "project", "deploy", "start")
        self.assertEqual(code, 0)
        self.assertIn("[sfc delta] vs run", out2)       # second run: delta
        self.assertIn("1 new, 1 resolved", out2)
        self.assertIn("classes/B.cls", out2)            # new error surfaced
        self.assertIn("classes/A.cls", out2)            # resolved error surfaced
        self.assertNotIn("Component C1  ApexClass  Succeeded", out2)  # rows not re-dumped

        rows = metering.read_rows()
        self.assertIsNone(rows[0]["delta_of"])
        self.assertEqual(rows[1]["delta_of"], rows[0]["id"])

    def test_deltas_toggle_off_gives_full_report(self):
        run_cli("on")
        cfg_path = Path(".sfc") / "config.json"
        import json
        cfg = json.loads(cfg_path.read_text())
        cfg["filters"]["deltas"] = False
        cfg_path.write_text(json.dumps(cfg))

        run_cli("run", "--", "sf", "project", "deploy", "start")
        _, out2 = run_cli("run", "--", "sf", "project", "deploy", "start")
        self.assertNotIn("[sfc delta]", out2)
        self.assertIn("component/row(s) Succeeded", out2)  # normal filtered report


if __name__ == "__main__":
    unittest.main()
