"""`sfc setup` - a multi-step wizard that wires sfc into a project with no manual
copy-paste. It installs the Agent Skill, registers the sfc MCP server in detected
agents, and seeds `.sfc/` config. sfc is ON by default; run `sfc off` to opt out.

Two ways to run, same core:
  * Interactively from a terminal (prompts with sensible defaults), or
  * Non-interactively from a coding agent / CI (`--yes`, `--agent`, `--json`).

`run_setup()` is the pure orchestration function (no prompts, returns a summary
dict) so the MCP server can expose it directly as a tool.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

from . import agents, state


def run_setup(
    root: Optional[Path] = None,
    agent_names: Optional[List[str]] = None,
    activate: bool = False,
    register_mcp: bool = True,
    install_skill: bool = True,
) -> Dict:
    """Perform setup and return a machine-readable summary of what happened."""
    root = Path(root).resolve() if root else state.find_root()
    if not agent_names:
        detected = agents.detect_agents(root)
        agent_names = detected or ["agents"]

    summary: Dict = {
        "root": str(root),
        "agents": list(agent_names),
        "skills_installed": [],
        "mcp_registered": [],
        "mcp_command": agents.mcp_launch_command(),
        "config": None,
        "active": False,
    }

    if install_skill:
        for subdir in agents.skill_targets(agent_names):
            try:
                dest = agents.install_skill(root, subdir)
                summary["skills_installed"].append(str(dest))
            except OSError as exc:
                summary["skills_installed"].append("ERROR {}: {}".format(subdir, exc))

    if register_mcp:
        for name in agent_names:
            try:
                path = agents.register_mcp(root, name)
                if path is not None:
                    summary["mcp_registered"].append(str(path))
            except OSError as exc:
                summary["mcp_registered"].append("ERROR {}: {}".format(name, exc))

    summary["config"] = str(state.ensure_config(root))

    if activate:
        state.set_active(True, root)
    summary["active"] = state.is_active(root)
    return summary


# --------------------------------------------------------------------------- #
# CLI front-end (interactive + non-interactive)
# --------------------------------------------------------------------------- #

def _interactive(args) -> bool:
    if getattr(args, "yes", False) or getattr(args, "non_interactive", False):
        return False
    if getattr(args, "json", False):
        return False
    return sys.stdin.isatty() and sys.stdout.isatty()


def _ask(prompt: str, default: str = "") -> str:
    try:
        resp = input(prompt).strip()
    except EOFError:
        return default
    return resp or default


def _ask_yes(prompt: str, default: bool = True) -> bool:
    suffix = " [Y/n] " if default else " [y/N] "
    resp = _ask(prompt + suffix).lower()
    if not resp:
        return default
    return resp in ("y", "yes")


def run(args) -> int:
    root = state.find_root()
    interactive = _interactive(args)

    # ---- resolve target agents -------------------------------------------- #
    if getattr(args, "agent", None):
        agent_names = list(args.agent)
    else:
        detected = agents.detect_agents(root)
        agent_names = detected or ["agents"]

    unknown = [a for a in agent_names if a not in agents.AGENTS]
    if unknown:
        print("[sfc setup] unknown agent(s): {}. Known: {}".format(
            ", ".join(unknown), ", ".join(agents.AGENTS)))
        return 2

    activate = bool(getattr(args, "activate", False))
    keep_off = False

    if interactive:
        print("sf-compress setup")
        print("=================")
        print("Step 1/4  Project root: {}".format(root))
        if not _ask_yes("          Use this as the project root?"):
            print("          Run the wizard from your project directory instead.")
            return 1

        detected = agents.detect_agents(root)
        print("Step 2/4  Agents detected: {}".format(
            ", ".join(detected) if detected else "none (will use universal .agents/skills)"))
        chosen = _ask("          Configure which agent(s)? [{}] ".format(
            ",".join(agent_names)))
        if chosen:
            agent_names = [a.strip() for a in chosen.replace(",", " ").split()]
            unknown = [a for a in agent_names if a not in agents.AGENTS]
            if unknown:
                print("          unknown agent(s): {}".format(", ".join(unknown)))
                return 2

        subdirs = agents.skill_targets(agent_names)
        print("Step 3/4  Will install the skill to: {}".format(", ".join(subdirs)))
        mcp_agents = [a for a in agent_names if agents.AGENTS[a].get("mcp_config")]
        if mcp_agents:
            print("          Will register the MCP server in: {}".format(
                ", ".join(agents.AGENTS[a]["mcp_config"] for a in mcp_agents)))
        if not _ask_yes("          Proceed?"):
            return 1

        print("Step 4/4  sfc is ON by default (dev-support compression active).")
        keep_off = _ask_yes("          Keep it off for now (sfc off)?", default=False)

    # ---- do the work ------------------------------------------------------ #
    summary = run_setup(
        root=root,
        agent_names=agent_names,
        activate=activate,
    )

    # Honor an explicit opt-out last, so it wins over `--activate`/default-ON.
    if keep_off:
        state.set_active(False, root)
        summary["active"] = state.is_active(root)

    if getattr(args, "json", False):
        print(json.dumps(summary, indent=2))
        return 0

    print("")
    print("[sfc setup] done.")
    print("  root:            {}".format(summary["root"]))
    print("  agents:          {}".format(", ".join(summary["agents"])))
    for p in summary["skills_installed"]:
        print("  skill installed: {}".format(p))
    if summary["mcp_registered"]:
        for p in summary["mcp_registered"]:
            print("  mcp registered:  {}".format(p))
        print("  mcp command:     {}".format(" ".join(summary["mcp_command"])))
        print("  -> restart / reload your agent so it picks up the MCP server.")
    else:
        print("  mcp:             (no MCP config for the selected agent(s))")
    print("  config:          {}".format(summary["config"]))
    print("  state:           {}".format("ACTIVE" if summary["active"] else "OFF (run `sfc on` when you start dev work)"))
    return 0
