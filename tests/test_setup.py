"""Tests for the setup wizard, agent registry, skill install, and MCP registration."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from sfc import agents, setup_wizard, state  # noqa: E402


class TestSkillAsset(unittest.TestCase):
    def test_skill_text_loads(self):
        txt = agents.skill_text()
        self.assertIn("sf-compress", txt)
        self.assertIn("dev-support", txt)

    def test_repo_copy_in_sync_with_packaged(self):
        # drift guard: the browsable repo-root skill must match the bundled asset
        packaged = (REPO / "src" / "sfc" / "assets" / "skills" / "sf-compress" / "SKILL.md").read_text()
        repo_copy = (REPO / "skills" / "sf-compress" / "SKILL.md").read_text()
        self.assertEqual(packaged, repo_copy)


class TestAgentsRegistry(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        os.chdir(self.root)

    def tearDown(self):
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def test_install_skill_writes_content(self):
        dest = agents.install_skill(self.root, ".agents/skills")
        self.assertTrue(dest.exists())
        self.assertEqual(dest, self.root / ".agents/skills/sf-compress/SKILL.md")
        self.assertIn("sf-compress", dest.read_text())

    def test_skill_targets_dedup(self):
        # cursor's own subdir + universal, no dupes
        targets = agents.skill_targets(["cursor", "agents"])
        self.assertIn(".agents/skills", targets)
        self.assertIn(".cursor/skills", targets)
        self.assertEqual(len(targets), len(set(targets)))

    def test_detect_agents(self):
        self.assertEqual(agents.detect_agents(self.root), [])
        (self.root / ".cursor").mkdir()
        self.assertIn("cursor", agents.detect_agents(self.root))
        (self.root / ".claude").mkdir()
        detected = agents.detect_agents(self.root)
        self.assertIn("cursor", detected)
        self.assertIn("claude", detected)

    def test_register_mcp_creates_config(self):
        path = agents.register_mcp(self.root, "cursor")
        self.assertEqual(path, self.root / ".cursor/mcp.json")
        data = json.loads(path.read_text())
        self.assertIn("sf-compress", data["mcpServers"])
        entry = data["mcpServers"]["sf-compress"]
        self.assertTrue(entry["command"])
        self.assertIn("mcp", entry["args"])

    def test_register_mcp_preserves_existing_servers(self):
        cfg = self.root / ".cursor/mcp.json"
        cfg.parent.mkdir(parents=True)
        cfg.write_text(json.dumps({"mcpServers": {"other": {"command": "x"}}}))
        agents.register_mcp(self.root, "cursor")
        data = json.loads(cfg.read_text())
        self.assertIn("other", data["mcpServers"])          # preserved
        self.assertIn("sf-compress", data["mcpServers"])    # added

    def test_register_mcp_none_for_universal(self):
        self.assertIsNone(agents.register_mcp(self.root, "agents"))


class TestSetupWizard(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        os.chdir(self.root)

    def tearDown(self):
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def test_run_setup_full(self):
        summary = setup_wizard.run_setup(root=self.root, agent_names=["cursor"])
        # skill installed to universal + cursor subdir
        self.assertTrue(any(".agents/skills" in p for p in summary["skills_installed"]))
        self.assertTrue(any(".cursor/skills" in p for p in summary["skills_installed"]))
        # mcp registered for cursor
        self.assertTrue(any("mcp.json" in p for p in summary["mcp_registered"]))
        # config seeded; sfc is ON by default (no state.json written => active)
        self.assertTrue(Path(summary["config"]).exists())
        self.assertTrue(summary["active"])
        self.assertTrue(state.is_active(self.root))

    def test_run_setup_defaults_to_universal_when_no_agent(self):
        summary = setup_wizard.run_setup(root=self.root)
        self.assertEqual(summary["agents"], ["agents"])
        self.assertEqual(summary["mcp_registered"], [])

    def test_run_setup_activate(self):
        summary = setup_wizard.run_setup(root=self.root, agent_names=["agents"], activate=True)
        self.assertTrue(summary["active"])
        self.assertTrue(state.is_active(self.root))


if __name__ == "__main__":
    unittest.main()
