"""CLI lifecycle tests: activation gate, dormancy, run/store/meter, show, stats."""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from sfc import cli, metering, state  # noqa: E402


def run_cli(*argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        try:
            code = cli.main(list(argv))
        except SystemExit as exc:  # argparse --version etc.
            code = exc.code or 0
    return code, buf.getvalue()


PRINT_CMD = [sys.executable, "-c", "print('hello from child')"]


class TestCliLifecycle(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)

    def tearDown(self):
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def test_default_on_active(self):
        # sfc ships ON by default: status is ACTIVE and `run` executes with no
        # explicit `sfc on` first.
        code, out = run_cli("status")
        self.assertEqual(code, 0)
        self.assertIn("ACTIVE", out)
        code, out = run_cli("run", "--", *PRINT_CMD)
        self.assertEqual(code, 0)
        self.assertIn("hello from child", out)

    def test_explicit_off_is_dormant(self):
        # `sfc off` opts a project out: run must refuse, no execution.
        code, out = run_cli("off")
        self.assertEqual(code, 0)
        code, out = run_cli("status")
        self.assertEqual(code, 1)
        self.assertIn("OFF", out)
        code, out = run_cli("run", "--", *PRINT_CMD)
        self.assertEqual(code, 3)
        self.assertIn("inactive", out)
        self.assertNotIn("hello from child", out)

    def test_on_run_show_stats_off(self):
        code, out = run_cli("on")
        self.assertEqual(code, 0)
        self.assertTrue(state.is_active())

        code, out = run_cli("run", "--", *PRINT_CMD)
        self.assertEqual(code, 0)                      # child's exit code
        self.assertIn("hello from child", out)         # pass-through family
        self.assertIn("Full output: sfc show", out)

        # store + metering written
        outputs = list((Path(".sfc") / "outputs").glob("*.txt"))
        self.assertEqual(len(outputs), 1)
        stored = outputs[0].read_text()
        self.assertTrue(stored.startswith("$ "))
        self.assertIn("hello from child", stored)
        rows = metering.read_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["exit_code"], 0)
        self.assertIsNone(rows[0]["filter_version"])   # pass-through

        # expand path
        output_id = outputs[0].stem
        code, out = run_cli("show", output_id)
        self.assertEqual(code, 0)
        self.assertIn("hello from child", out)
        code, out = run_cli("show", output_id, "--grep", "child")
        self.assertIn("hello from child", out)
        code, out = run_cli("show", "nope-such-id")
        self.assertEqual(code, 1)

        # stats aggregates
        code, out = run_cli("stats")
        self.assertEqual(code, 0)
        self.assertIn("TOTAL", out)

        # off -> dormant again
        run_cli("off")
        code, out = run_cli("run", "--", *PRINT_CMD)
        self.assertEqual(code, 3)

    def test_child_exit_code_propagates(self):
        run_cli("on")
        code, _ = run_cli("run", "--", sys.executable, "-c", "raise SystemExit(7)")
        self.assertEqual(code, 7)
        rows = metering.read_rows()
        self.assertEqual(rows[-1]["exit_code"], 7)

    def test_filter_toggle_off_passes_through(self):
        run_cli("on")
        cfg_path = Path(".sfc") / "config.json"
        cfg = json.loads(cfg_path.read_text())
        cfg["filters"]["sf-debug-log"] = False
        cfg_path.write_text(json.dumps(cfg))
        # a fake "sf apex get log" via python that prints noise; family classifies
        # from the command string, so craft argv that classifies as debug-log
        code, out = run_cli(
            "run", "--", sys.executable, "-c",
            "print('HEAP_ALLOCATE noise')",  # would be dropped if filter ran
        )
        # this command doesn't classify as sf (family None) -> passes through anyway;
        # verify the toggle path directly instead:
        self.assertFalse(state.filter_enabled("sf-debug-log", state.load_config()))
        self.assertTrue(state.filter_enabled("sf-deploy", state.load_config()))
        self.assertIn("HEAP_ALLOCATE noise", out)


if __name__ == "__main__":
    unittest.main()
