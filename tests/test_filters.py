"""Golden tests: filters vs synthetic corpus fixtures + signal-preservation.

Run: python3 -m unittest discover tests   (from the repo root, with src on path)

The original golden tests ran against a real corpus captured from a private
Salesforce project. That client-derived data was removed from the repo (see
MEMORY.md sec.5/sec.10); `tests/synth.py` reproduces the shape of each command
family's output so we still assert the Phase 0 reduction ratios and the
never-drop-signal guarantees, with zero proprietary data shipped.
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from sfc import filters  # noqa: E402
from sfc.filters.common import est_tokens, normalize_lines  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import synth  # noqa: E402


def reduction(raw, emitted):
    rt, et = est_tokens(len(raw)), est_tokens(len(emitted))
    return 100 * (1 - et / rt) if rt else 0.0


class TestClassification(unittest.TestCase):
    def test_families(self):
        cases = {
            "sf project deploy start -d force-app": "sf-deploy",
            "sf project deploy validate -d DEV": "sf-deploy",
            "sfdx force:source:deploy -p foo": "sf-deploy",
            "sf project retrieve preview": "sf-table",
            "sf project deploy preview": "sf-table",
            "sf org list metadata --metadata-type ApexClass": "sf-table",
            "sf org list --verbose": "sf-table",
            "sf apex run test --code-coverage": "sf-apex-test",
            "sf apex get log -i 07L...": "sf-debug-log",
            "sf apex tail log": "sf-debug-log",
            "sf data query -q 'SELECT Id FROM Account' --json": "sf-json",
            "sf sobject describe -s Account --json": "sf-json",
            "git log --stat -20": None,
            "npm ls": None,
            "grep -r foo .": None,
        }
        for cmd, want in cases.items():
            self.assertEqual(filters.classify(cmd), want, cmd)

    def test_deploy_with_json_flag_uses_json_filter(self):
        self.assertEqual(filters.classify("sf project deploy start --json"), "sf-json")


class TestSyntheticGolden(unittest.TestCase):
    """Reduction ratios must reproduce Phase 0 findings on synthetic fixtures."""

    def test_retrieve_preview_99pct(self):
        body = synth.table_output(n_rows=2000)
        emitted, _ = filters.apply("sf-table", body)
        self.assertGreaterEqual(reduction(body, emitted), 99.0)
        self.assertIn("table row(s)", emitted)

    def test_list_metadata_98pct(self):
        body = synth.table_output(n_rows=1000, kind="CustomField")
        emitted, _ = filters.apply("sf-table", body)
        self.assertGreaterEqual(reduction(body, emitted), 98.0)

    def test_debug_log_99pct_and_signal_preserved(self):
        body, signals = synth.debug_log(noise=5000, n_debug=6)
        emitted, _ = filters.apply("sf-debug-log", body)
        self.assertGreaterEqual(reduction(body, emitted), 99.0)
        for line in signals:
            self.assertIn(line, emitted)  # every USER_DEBUG / FATAL / LIMIT survives

    def test_query_json_to_csv_80pct(self):
        body = synth.query_json(n=500)
        emitted, _ = filters.apply("sf-json", body)
        self.assertGreaterEqual(reduction(body, emitted), 80.0)
        self.assertIn("500 records", emitted)

    def test_describe_json_minify_25pct(self):
        body = synth.describe_json(n_fields=300)
        emitted, _ = filters.apply("sf-json", body)
        self.assertGreaterEqual(reduction(body, emitted), 25.0)

    def test_deploy_validate_structure(self):
        body = synth.deploy_report(n_components=300)
        emitted, _ = filters.apply("sf-deploy", body)
        self.assertGreaterEqual(reduction(body, emitted), 50.0)
        self.assertIn("Status", emitted)
        self.assertIn("Missing ';'", emitted)   # error never dropped

    def test_apex_test_keeps_summary(self):
        body = synth.apex_test(n_pass=200)
        emitted, _ = filters.apply("sf-apex-test", body)
        for signal in ("=== Test Summary", "Outcome", "Pass Rate", "Fail Rate"):
            self.assertIn(signal, emitted)
        self.assertIn("AssertException", emitted)  # failure kept
        self.assertIn("RiskyClass", emitted)       # <75% coverage kept


class TestSignalPreservation(unittest.TestCase):
    def test_deploy_errors_never_dropped(self):
        raw = "\n".join(
            ["Component Foo  Succeeded"] * 200
            + ["Error  classes/Bad.cls  Missing semicolon (line 12)"]
            + ["Deploy ID: 0Af000000000001", "Status: Failed"]
        )
        emitted, _ = filters.apply("sf-deploy", raw)
        self.assertIn("Missing semicolon", emitted)
        self.assertIn("Status: Failed", emitted)
        self.assertIn("200", emitted)  # collapsed count reported
        self.assertNotIn("Component Foo  Succeeded", emitted)

    def test_apex_failures_never_dropped(self):
        raw = "\n".join(
            ["SomeTest.passing  Pass  120"] * 50
            + ["OtherTest.broken  Fail  System.AssertException: expected 1, got 2"]
            + ["HealthyClass  92%", "RiskyClass  40%  7,9,12"]
        )
        emitted, _ = filters.apply("sf-apex-test", raw)
        self.assertIn("System.AssertException", emitted)
        self.assertIn("RiskyClass", emitted)      # <75% coverage kept
        self.assertNotIn("HealthyClass  92%", emitted)

    def test_debug_log_keeps_signal_drops_noise(self):
        raw = "\n".join(
            ["12:00:00.1 (1)|HEAP_ALLOCATE|[72]|Bytes:3"] * 100
            + ["12:00:00.2 (2)|USER_DEBUG|[5]|DEBUG|checkpoint hit"]
            + ["12:00:00.3 (3)|FATAL_ERROR|System.NullPointerException"]
            + ["12:00:00.4 (4)|LIMIT_USAGE|[0]|SOQL|5|100"]
        )
        emitted, _ = filters.apply("sf-debug-log", raw)
        self.assertIn("checkpoint hit", emitted)
        self.assertIn("NullPointerException", emitted)
        self.assertIn("LIMIT_USAGE", emitted)
        self.assertNotIn("HEAP_ALLOCATE", emitted)

    def test_ansi_and_spinner_collapse(self):
        spinner = "".join("\rValidating... {}s".format(i) for i in range(500))
        raw = "\x1b[33m" + spinner + "\n\x1b[0mStatus: Succeeded and deployed\n"
        lines = normalize_lines(raw)
        # 500 repaint frames -> the final frame only
        self.assertEqual(sum(1 for ln in lines if "Validating" in ln), 1)
        self.assertNotIn("\x1b", "\n".join(lines))

    def test_unknown_family_passes_through(self):
        raw = "totally unrecognized output\nline two"
        emitted, version = filters.apply(None, raw)
        self.assertEqual(emitted, raw)
        self.assertIsNone(version)

    def test_json_garbage_falls_back(self):
        emitted, _ = filters.apply("sf-json", "not json at   all\n\n  really")
        self.assertEqual(emitted, "not json at all really")


if __name__ == "__main__":
    unittest.main()
