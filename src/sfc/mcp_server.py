"""`sfc mcp` - a minimal MCP stdio server exposing sfc to coding agents.

Line-delimited JSON-RPC 2.0 over stdin/stdout (MCP stdio transport,
protocolVersion 2024-11-05). Standard-library only. Registered in an agent's MCP
config by `sfc setup`, so the agent can install the skill, check status, route
Salesforce commands, and expand stored output as native tools - instead of the
user copy-pasting anything.

Tools that produce CLI output are implemented by capturing `cli.main(argv)`, so
behavior stays identical to the shell.
"""

import contextlib
import io
import json
import shlex
import sys
from typing import Dict, List, Optional

from . import __version__, agents, cli, setup_wizard, state

PROTOCOL_VERSION = "2024-11-05"


# --------------------------------------------------------------------------- #
# Tool implementations
# --------------------------------------------------------------------------- #

def _run_cli(argv: List[str]) -> Dict:
    """Run `cli.main(argv)`, capturing stdout/stderr. Returns a text result."""
    buf = io.StringIO()
    code = 0
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            code = cli.main(argv)
    except SystemExit as exc:  # argparse errors, etc.
        code = int(exc.code) if isinstance(exc.code, int) else (0 if exc.code is None else 2)
    except Exception as exc:  # pragma: no cover - defensive
        return _text("error: {}".format(exc), is_error=True)
    text = buf.getvalue().rstrip("\n")
    return _text(text if text else "(no output, exit {})".format(code), is_error=code not in (0, 1))


def _as_argv_list(value) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    return shlex.split(str(value))


def _t_status(_args: Dict) -> Dict:
    return _run_cli(["status"])


def _t_on(_args: Dict) -> Dict:
    return _run_cli(["on"])


def _t_off(_args: Dict) -> Dict:
    return _run_cli(["off"])


def _t_stats(_args: Dict) -> Dict:
    return _run_cli(["stats"])


def _t_run(args: Dict) -> Dict:
    cmd = _as_argv_list(args.get("command"))
    if not cmd:
        return _text("error: 'command' is required (array or string)", is_error=True)
    return _run_cli(["run", "--"] + cmd)


def _t_show(args: Dict) -> Dict:
    ident = args.get("id")
    if not ident:
        return _text("error: 'id' is required", is_error=True)
    argv = ["show", str(ident)]
    if args.get("grep"):
        argv += ["--grep", str(args["grep"])]
    if args.get("head"):
        argv += ["--head", str(int(args["head"]))]
    if args.get("tail"):
        argv += ["--tail", str(int(args["tail"]))]
    return _run_cli(argv)


def _t_graph(args: Dict) -> Dict:
    forwarded = _as_argv_list(args.get("args"))
    if not forwarded:
        return _text("error: 'args' is required, e.g. [\"query\", \"where is X used?\"]",
                     is_error=True)
    return _run_cli(["graph"] + forwarded)


def _t_setup(args: Dict) -> Dict:
    agent = args.get("agent")
    if isinstance(agent, str):
        agent = [agent]
    summary = setup_wizard.run_setup(
        agent_names=agent,
        activate=bool(args.get("activate", False)),
    )
    return _text(json.dumps(summary, indent=2))


def _t_install_skill(args: Dict) -> Dict:
    root = state.find_root()
    agent = args.get("agent")
    if isinstance(agent, str):
        agent = [agent]
    if not agent:
        agent = agents.detect_agents(root) or ["agents"]
    written = []
    for subdir in agents.skill_targets(agent):
        written.append(str(agents.install_skill(root, subdir)))
    return _text("installed skill to:\n" + "\n".join(written))


# name -> (handler, description, input schema)
TOOLS = {
    "sfc_setup": (
        _t_setup,
        "Wire sfc into this project (install the Agent Skill, register the MCP "
        "server, seed config). sfc is ON by default. Run this once per project.",
        {
            "type": "object",
            "properties": {
                "agent": {
                    "type": ["array", "string"],
                    "description": "Agent(s) to configure: cursor, claude, agents. "
                                   "Omit to auto-detect.",
                },
                "activate": {
                    "type": "boolean",
                    "description": "Also run `sfc on` (default false; only if the user asked).",
                },
            },
        },
    ),
    "sfc_install_skill": (
        _t_install_skill,
        "Install/refresh the sf-compress Agent Skill into this project's skills "
        "directories (no manual copy-paste).",
        {
            "type": "object",
            "properties": {
                "agent": {"type": ["array", "string"],
                          "description": "Target agent(s); omit to auto-detect."},
            },
        },
    ),
    "sfc_status": (
        _t_status,
        "Report whether sfc is ACTIVE or OFF for this project, plus filter toggles. "
        "Check this before routing any command through sfc.",
        {"type": "object", "properties": {}},
    ),
    "sfc_on": (
        _t_on,
        "Activate sfc for dev-support work. Only call if the user explicitly asks.",
        {"type": "object", "properties": {}},
    ),
    "sfc_off": (
        _t_off,
        "Deactivate sfc (fully dormant). Use when leaving dev-support work.",
        {"type": "object", "properties": {}},
    ),
    "sfc_run": (
        _t_run,
        "Run a Salesforce dev command through the compressor and return the "
        "compressed view (full raw output is stored; expand with sfc_show).",
        {
            "type": "object",
            "properties": {
                "command": {
                    "type": ["array", "string"],
                    "description": 'The command, e.g. ["sf","project","deploy","start","-d","force-app"].',
                },
            },
            "required": ["command"],
        },
    ),
    "sfc_show": (
        _t_show,
        "Expand a stored full raw output by id. Narrow with grep/head/tail; do not dump blindly.",
        {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "Output id (or unique prefix) from the footer."},
                "grep": {"type": "string", "description": "Only lines matching this regex."},
                "head": {"type": "integer", "description": "Only the first N lines."},
                "tail": {"type": "integer", "description": "Only the last N lines."},
            },
            "required": ["id"],
        },
    ),
    "sfc_stats": (
        _t_stats,
        "Token savings per command family (raw vs emitted).",
        {"type": "object", "properties": {}},
    ),
    "sfc_graph": (
        _t_graph,
        "Query the graphify-sf code graph to locate code/dependencies (needs the "
        "exploration-graph toggle). A first-pass locator - verify callers in source.",
        {
            "type": "object",
            "properties": {
                "args": {"type": ["array", "string"],
                         "description": 'e.g. ["query","where is AccountTrigger used?"].'},
            },
            "required": ["args"],
        },
    ),
}


def _text(text: str, is_error: bool = False) -> Dict:
    return {"content": [{"type": "text", "text": text}], "isError": bool(is_error)}


def _tool_specs() -> List[Dict]:
    return [
        {"name": name, "description": desc, "inputSchema": schema}
        for name, (_fn, desc, schema) in TOOLS.items()
    ]


def _call_tool(params: Dict) -> Dict:
    name = params.get("name")
    arguments = params.get("arguments") or {}
    entry = TOOLS.get(name)
    if entry is None:
        return _text("unknown tool: {}".format(name), is_error=True)
    handler = entry[0]
    try:
        return handler(arguments)
    except Exception as exc:  # tool errors are results, not protocol errors
        return _text("tool '{}' failed: {}".format(name, exc), is_error=True)


# --------------------------------------------------------------------------- #
# JSON-RPC / MCP protocol
# --------------------------------------------------------------------------- #

def _handle(msg: Dict) -> Optional[Dict]:
    mid = msg.get("id")
    method = msg.get("method")
    params = msg.get("params") or {}

    if method == "initialize":
        result = {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "sf-compress", "version": __version__},
        }
    elif method in ("notifications/initialized", "notifications/cancelled"):
        return None  # notification: no response
    elif method == "tools/list":
        result = {"tools": _tool_specs()}
    elif method == "tools/call":
        result = _call_tool(params)
    elif method == "ping":
        result = {}
    else:
        if mid is None:
            return None
        return {"jsonrpc": "2.0", "id": mid,
                "error": {"code": -32601, "message": "method not found: {}".format(method)}}

    if mid is None:
        return None
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def serve(stdin=None, stdout=None) -> int:
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        try:
            resp = _handle(msg)
        except Exception as exc:  # pragma: no cover - defensive
            mid = msg.get("id") if isinstance(msg, dict) else None
            if mid is None:
                continue
            resp = {"jsonrpc": "2.0", "id": mid,
                    "error": {"code": -32603, "message": "internal error: {}".format(exc)}}
        if resp is not None:
            stdout.write(json.dumps(resp) + "\n")
            stdout.flush()
    return 0
