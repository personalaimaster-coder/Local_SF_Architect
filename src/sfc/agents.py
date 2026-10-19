"""Agent/IDE integration for sfc.

Locate the packaged Agent Skill, install it into a project's agent-skills
directory, and register the sfc MCP server in an agent's MCP config - so a coding
agent (or the `sfc setup` wizard) can wire everything up with no manual
copy-paste. Standard-library only.

The registry is intentionally small and data-driven. Each agent entry declares:
  skills_subdir : where that agent loads project Agent Skills (relative to root)
  mcp_config    : the agent's project MCP config file (None => no MCP support)
  detect        : paths whose existence suggests the agent is used in this project
"""

import json
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional

SKILL_NAME = "sf-compress"
MCP_SERVER_NAME = "sf-compress"

# Universal cross-tool convention. Always installed to, in addition to any
# agent-specific location, so the skill is found regardless of loader.
UNIVERSAL_SKILLS_SUBDIR = ".agents/skills"

AGENTS: Dict[str, Dict] = {
    "cursor": {
        "label": "Cursor",
        "skills_subdir": ".cursor/skills",
        "mcp_config": ".cursor/mcp.json",
        "detect": [".cursor"],
    },
    "claude": {
        "label": "Claude Code",
        "skills_subdir": ".claude/skills",
        "mcp_config": ".mcp.json",
        "detect": [".claude", "CLAUDE.md", ".mcp.json"],
    },
    # Universal target: skill only (no standard project MCP config location).
    "agents": {
        "label": "Generic (.agents)",
        "skills_subdir": UNIVERSAL_SKILLS_SUBDIR,
        "mcp_config": None,
        "detect": [".agents"],
    },
}


# --------------------------------------------------------------------------- #
# Skill asset
# --------------------------------------------------------------------------- #

def skill_text() -> str:
    """Return the bundled SKILL.md text (works installed or from a source tree)."""
    # 1) packaged data (wheel / pip / pipx install)
    try:
        from importlib.resources import files  # py3.9+
        res = files("sfc").joinpath("assets/skills/{}/SKILL.md".format(SKILL_NAME))
        return res.read_text(encoding="utf-8")
    except Exception:
        pass
    # 2) source-checkout fallbacks
    here = Path(__file__).resolve()
    for cand in (
        here.parent / "assets" / "skills" / SKILL_NAME / "SKILL.md",
        here.parent.parent.parent / "skills" / SKILL_NAME / "SKILL.md",
    ):
        if cand.exists():
            return cand.read_text(encoding="utf-8")
    raise FileNotFoundError("bundled sf-compress SKILL.md not found")


def install_skill(root: Path, subdir: str) -> Path:
    """Write the skill into `<root>/<subdir>/sf-compress/SKILL.md`. Returns path."""
    dest = root / subdir / SKILL_NAME / "SKILL.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(skill_text(), encoding="utf-8")
    return dest


def skill_targets(agent_names: List[str]) -> List[str]:
    """Deduped list of skills subdirs to install to (universal + per-agent)."""
    subdirs = [UNIVERSAL_SKILLS_SUBDIR]
    for name in agent_names:
        sub = AGENTS.get(name, {}).get("skills_subdir")
        if sub and sub not in subdirs:
            subdirs.append(sub)
    return subdirs


# --------------------------------------------------------------------------- #
# MCP registration
# --------------------------------------------------------------------------- #

def mcp_launch_command() -> List[str]:
    """Best-effort command an agent should use to launch the sfc MCP server."""
    exe = shutil.which("sfc")
    if exe:
        return [exe, "mcp"]
    # source / non-PATH install: python -m sfc mcp (needs sfc importable)
    return [sys.executable, "-m", "sfc", "mcp"]


def mcp_server_entry() -> Dict:
    cmd = mcp_launch_command()
    return {"command": cmd[0], "args": cmd[1:]}


def register_mcp(root: Path, agent_name: str) -> Optional[Path]:
    """Merge the sfc MCP server into an agent's MCP config, preserving others.

    Returns the config path written, or None if the agent has no MCP config.
    """
    spec = AGENTS.get(agent_name, {})
    rel = spec.get("mcp_config")
    if not rel:
        return None
    path = root / rel
    data: Dict = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
    if not isinstance(data, dict):
        data = {}
    servers = data.get("mcpServers")
    if not isinstance(servers, dict):
        servers = {}
        data["mcpServers"] = servers
    servers[MCP_SERVER_NAME] = mcp_server_entry()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


# --------------------------------------------------------------------------- #
# Detection
# --------------------------------------------------------------------------- #

def detect_agents(root: Path) -> List[str]:
    """Agent names that appear to be in use in this project (excludes universal)."""
    found: List[str] = []
    for name, spec in AGENTS.items():
        if name == "agents":
            continue
        for hint in spec.get("detect", []):
            if (root / hint).exists():
                found.append(name)
                break
    return found
