"""`sfc bench` - raw CLI vs Salesforce DX MCP token comparison.

For each command family it runs the raw `sf` command and the equivalent DX MCP
tool (discovered at runtime via tools/list, so it tolerates the beta server
evolving), records raw token counts of both transports plus sfc's filtered size,
and writes a markdown comparison report. Run on a machine with an authenticated
org; MCP tool names/args may need per-version tweaks (see docs/org-workbench.md).
"""

import shlex
import subprocess
from pathlib import Path

from .. import filters
from ..filters.common import est_tokens
from .mcp_client import MCPClient, MCPError, result_text

DEFAULT_QUERY = "SELECT Id, Name FROM Account LIMIT 200"
# Adjustable; the DX MCP server is spawned over stdio. See runbook.
DEFAULT_MCP_CMD = "npx -y @salesforce/mcp --orgs DEFAULT_TARGET_ORG --toolsets all"


def _operations(args):
    q = args.query or DEFAULT_QUERY
    obj = args.object or "Account"
    return [
        {"name": "query", "family": "sf-json",
         "cli": ["sf", "data", "query", "-q", q, "--json"],
         "mcp_keywords": ["query", "soql"], "mcp_args": {"query": q}},
        {"name": "describe", "family": "sf-json",
         "cli": ["sf", "sobject", "describe", "-s", obj, "--json"],
         "mcp_keywords": ["describe", "sobject"], "mcp_args": {"sobject": obj}},
        {"name": "retrieve-preview", "family": "sf-table",
         "cli": ["sf", "project", "retrieve", "preview"],
         "mcp_keywords": ["retrieve", "preview"], "mcp_args": {}},
        {"name": "test-run", "family": "sf-apex-test",
         "cli": ["sf", "apex", "run", "test", "--result-format", "human",
                 "--synchronous", "--code-coverage"],
         "mcp_keywords": ["test"], "mcp_args": {}},
    ]


def _cli_tokens(argv, family):
    try:
        p = subprocess.run(argv, capture_output=True, text=True, errors="replace")
    except FileNotFoundError:
        return None, None
    raw = p.stdout or ""
    if p.stderr:
        raw += ("\n" if raw and not raw.endswith("\n") else "") + p.stderr
    emitted, _ = filters.apply(family, raw)
    return est_tokens(len(raw)), est_tokens(len(emitted))


def _pick_tool(tools, keywords):
    for t in tools:
        hay = (t.get("name", "") + " " + t.get("description", "")).lower()
        if any(k in hay for k in keywords):
            return t.get("name")
    return None


def _n(v):
    return "n/a" if v is None else str(v)


def _terser(cli_raw, mcp_raw):
    if cli_raw is None or mcp_raw is None:
        return "-"
    if mcp_raw < cli_raw:
        return "MCP"
    if cli_raw < mcp_raw:
        return "CLI"
    return "tie"


def _write_report(out_path, ops, tools, mcp_ok, mcp_err=None):
    lines = [
        "# sfc bench - raw CLI vs Salesforce DX MCP (token comparison)",
        "",
        "Tokens are chars/4 estimates. **CLI filtered** = after sfc's family filter.",
        "Route each family to the terser transport; wrap whichever is verbose.",
        "",
    ]
    if not mcp_ok:
        lines.append("> MCP side unavailable this run ({}). CLI numbers still valid.".format(
            mcp_err or "no MCP server"))
        lines.append("")
    lines.append("| operation | CLI raw | CLI filtered (sfc) | MCP tool | MCP raw | terser |")
    lines.append("|---|--:|--:|---|--:|---|")
    for op in ops:
        lines.append("| {} | {} | {} | {} | {} | {} |".format(
            op["name"], _n(op.get("cli_raw")), _n(op.get("cli_filtered")),
            op.get("mcp_tool") or "-", _n(op.get("mcp_raw")),
            _terser(op.get("cli_raw"), op.get("mcp_raw"))))
    lines.append("")
    names = ", ".join(t.get("name", "?") for t in tools) if tools else "(none discovered)"
    lines.append("Discovered MCP tools: {}".format(names))
    lines.append("")
    Path(out_path).write_text("\n".join(lines) + "\n")


def run(args):
    ops = _operations(args)
    out_path = Path(args.out or "bench-report.md")

    print("[sfc bench] measuring raw CLI output per family...")
    for op in ops:
        cr, cf = _cli_tokens(op["cli"], op["family"])
        op["cli_raw"], op["cli_filtered"] = cr, cf

    # shlex.split honors quoting so interpreter/script paths containing spaces work
    # (e.g. a project directory with spaces); identical to .split() for the unquoted
    # default command.
    mcp_cmd = shlex.split(args.mcp_cmd or DEFAULT_MCP_CMD)
    print("[sfc bench] querying DX MCP server: {}".format(" ".join(mcp_cmd)))
    tools, mcp_ok, mcp_err = [], True, None
    try:
        with MCPClient(mcp_cmd) as client:
            tools = client.list_tools()
            for op in ops:
                name = _pick_tool(tools, op["mcp_keywords"])
                op["mcp_tool"] = name
                if not name:
                    op["mcp_raw"] = None
                    continue
                try:
                    res = client.call_tool(name, op["mcp_args"])
                    op["mcp_raw"] = est_tokens(len(result_text(res)))
                except MCPError:
                    op["mcp_raw"] = None
    except (MCPError, OSError) as exc:
        mcp_ok, mcp_err = False, str(exc)
        for op in ops:
            op.setdefault("mcp_tool", None)
            op.setdefault("mcp_raw", None)

    _write_report(out_path, ops, tools, mcp_ok, mcp_err)
    print("[sfc bench] wrote {}".format(out_path))
    return 0
