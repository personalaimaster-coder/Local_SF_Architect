"""sfc command-line interface.

Commands:
  sfc on                     activate for this project (dev-support work)
  sfc off                    deactivate (fully dormant; use during analysis/architecture)
  sfc status                 show active/inactive + filter toggles
  sfc run -- <command...>    execute a command through the compressor
  sfc show <id> [--grep PAT] [--head N] [--tail N]   expand a stored full output
  sfc stats                  token savings per command family
"""

import argparse
import re
import sys

from . import __version__, agents, graph, metering, runner, setup_wizard, state, store
from .filters.common import est_tokens
from .workbench import bench as _bench
from .workbench import collect as _collect


def _cmd_on(_args) -> int:
    state.set_active(True)
    print("[sfc] ACTIVE for {} - route Salesforce dev commands through: sfc run -- <cmd>".format(
        state.find_root()))
    return 0


def _cmd_off(_args) -> int:
    state.set_active(False)
    print("[sfc] OFF - fully dormant. Use raw commands directly.")
    return 0


def _cmd_status(_args) -> int:
    active = state.is_active()
    print("[sfc] {}".format("ACTIVE" if active else "OFF"))
    if active:
        cfg = state.load_config()
        toggles = ", ".join(
            "{}={}".format(k, "on" if v else "off")
            for k, v in sorted(cfg.get("filters", {}).items())
        )
        print("[sfc] filters: {}".format(toggles))
        print("[sfc] usage: sfc run -- <command> | sfc show <id> | sfc stats")
    return 0 if active else 1


def _cmd_run(args) -> int:
    argv = list(args.command)
    if argv and argv[0] == "--":
        argv = argv[1:]
    return runner.run(argv)


def _cmd_graph(args) -> int:
    argv = list(args.args)
    if argv and argv[0] == "--":
        argv = argv[1:]
    return graph.run(argv)


def _cmd_show(args) -> int:
    path = store.load_path(args.id)
    if path is None:
        print("[sfc] no stored output matches id '{}'".format(args.id))
        return 1
    text = path.read_text(errors="replace")
    lines = text.splitlines()
    if args.grep:
        try:
            rx = re.compile(args.grep, re.IGNORECASE)
        except re.error as exc:
            print("[sfc] bad --grep pattern: {}".format(exc))
            return 2
        lines = [ln for ln in lines if rx.search(ln)]
    if args.head:
        lines = lines[: args.head]
    elif args.tail:
        lines = lines[-args.tail:]
    print("\n".join(lines))
    return 0


def _cmd_setup(args) -> int:
    return setup_wizard.run(args)


def _cmd_install_skill(args) -> int:
    root = state.find_root()
    agent = list(args.agent) if getattr(args, "agent", None) else (
        agents.detect_agents(root) or ["agents"])
    unknown = [a for a in agent if a not in agents.AGENTS]
    if unknown:
        print("[sfc] unknown agent(s): {}. Known: {}".format(
            ", ".join(unknown), ", ".join(agents.AGENTS)))
        return 2
    subdirs = [args.dest] if getattr(args, "dest", None) else agents.skill_targets(agent)
    for subdir in subdirs:
        dest = agents.install_skill(root, subdir)
        print("[sfc] skill installed: {}".format(dest))
    return 0


def _cmd_mcp(_args) -> int:
    from . import mcp_server
    return mcp_server.serve()


def _cmd_collect(args) -> int:
    return _collect.run(args)


def _cmd_bench(args) -> int:
    return _bench.run(args)


def _cmd_stats(_args) -> int:
    rows = metering.read_rows()
    if not rows:
        print("[sfc] no metrics yet ({}/metrics.jsonl is empty)".format(state.SFC_DIRNAME))
        return 0
    agg = {}
    for r in rows:
        fam = r.get("family", "other")
        a = agg.setdefault(fam, {"calls": 0, "raw": 0, "emitted": 0})
        a["calls"] += 1
        a["raw"] += r.get("raw_tokens", 0)
        a["emitted"] += r.get("emitted_tokens", 0)
    total_raw = sum(a["raw"] for a in agg.values())
    total_emitted = sum(a["emitted"] for a in agg.values())
    print("{:<16} {:>6} {:>12} {:>12} {:>8}".format(
        "family", "calls", "raw_tokens", "emitted", "saved%"))
    for fam in sorted(agg, key=lambda f: -agg[f]["raw"]):
        a = agg[fam]
        saved = 100 * (1 - a["emitted"] / a["raw"]) if a["raw"] else 0.0
        print("{:<16} {:>6} {:>12} {:>12} {:>7.1f}%".format(
            fam, a["calls"], a["raw"], a["emitted"], saved))
    total_saved = 100 * (1 - total_emitted / total_raw) if total_raw else 0.0
    print("{:<16} {:>6} {:>12} {:>12} {:>7.1f}%".format(
        "TOTAL", len(rows), total_raw, total_emitted, total_saved))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sfc",
        description="Salesforce dev-support context compressor for AI coding agents.",
    )
    parser.add_argument("--version", action="version", version="sfc " + __version__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_setup = sub.add_parser(
        "setup", help="wizard: install the skill, register the MCP server, seed config")
    p_setup.add_argument("--agent", action="append",
                         help="target agent (cursor|claude|agents); repeatable; omit to auto-detect")
    p_setup.add_argument("--yes", "-y", action="store_true",
                         help="non-interactive; accept defaults")
    p_setup.add_argument("--non-interactive", action="store_true",
                         help="never prompt (same as --yes for agents/CI)")
    p_setup.add_argument("--activate", action="store_true",
                         help="also run `sfc on` (default: leave OFF)")
    p_setup.add_argument("--json", action="store_true",
                         help="print a machine-readable summary (for agents)")
    p_setup.set_defaults(fn=_cmd_setup)

    p_iskill = sub.add_parser(
        "install-skill", help="install/refresh just the Agent Skill (no MCP, no config)")
    p_iskill.add_argument("--agent", action="append",
                          help="target agent; repeatable; omit to auto-detect")
    p_iskill.add_argument("--dest", help="explicit skills subdir (overrides agent defaults)")
    p_iskill.set_defaults(fn=_cmd_install_skill)

    sub.add_parser(
        "mcp", help="run the sfc MCP stdio server (registered by `sfc setup`)"
    ).set_defaults(fn=_cmd_mcp)

    sub.add_parser("on", help="activate sfc for this project").set_defaults(fn=_cmd_on)
    sub.add_parser("off", help="deactivate sfc (fully dormant)").set_defaults(fn=_cmd_off)
    sub.add_parser("status", help="show activation state and filter toggles").set_defaults(fn=_cmd_status)

    p_run = sub.add_parser("run", help="run a command through the compressor")
    p_run.add_argument("command", nargs=argparse.REMAINDER,
                       help="the command to execute, e.g. sfc run -- sf project deploy start")
    p_run.set_defaults(fn=_cmd_run)

    p_graph = sub.add_parser(
        "graph",
        help="query the graphify-sf code graph (exploration; needs exploration-graph on)")
    p_graph.add_argument("args", nargs=argparse.REMAINDER,
                         help='e.g. sfc graph query "where is AccountTrigger used?"')
    p_graph.set_defaults(fn=_cmd_graph)

    p_show = sub.add_parser("show", help="print a stored full raw output")
    p_show.add_argument("id", help="output id (or unique prefix) from the [sfc <id>] footer")
    p_show.add_argument("--grep", help="only lines matching this regex (case-insensitive)")
    p_show.add_argument("--head", type=int, help="only the first N lines")
    p_show.add_argument("--tail", type=int, help="only the last N lines")
    p_show.set_defaults(fn=_cmd_show)

    sub.add_parser("stats", help="token savings per command family").set_defaults(fn=_cmd_stats)

    p_collect = sub.add_parser(
        "collect", help="org workbench: re-collect real CLI fixtures (needs an org)")
    p_collect.add_argument("--out", help="output directory (default: collected)")
    p_collect.add_argument("--allow-org-writes", action="store_true",
                           help="include org-side steps (apex test, deploy validate)")
    p_collect.add_argument("--query", help="SOQL for the data-query fixture")
    p_collect.add_argument("--object", help="sObject for the describe fixture (default: Account)")
    p_collect.add_argument("--deploy-dir", help="package dir for deploy validate (default: force-app)")
    p_collect.set_defaults(fn=_cmd_collect)

    p_bench = sub.add_parser(
        "bench", help="org workbench: benchmark raw CLI vs Salesforce DX MCP (needs an org)")
    p_bench.add_argument("--out", help="report path (default: bench-report.md)")
    p_bench.add_argument("--query", help="SOQL for the query benchmark")
    p_bench.add_argument("--object", help="sObject for the describe benchmark (default: Account)")
    p_bench.add_argument("--mcp-cmd", help="command to launch the DX MCP stdio server")
    p_bench.set_defaults(fn=_cmd_bench)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
