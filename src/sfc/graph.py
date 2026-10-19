"""graphify-sf integration: the exploration-graph module (Pillar B).

graphify-sf (MIT, PyPI) parses an SFDX project OFFLINE into a queryable knowledge
graph and answers "where is X used / what depends on Y" within a token budget --
exactly the exploration-bloat problem sfc's runtime-output filters do not touch.

Rather than take a hard dependency (graphify-sf needs Python 3.10+ and several
libs; sfc is stdlib-only 3.9+), we integrate through a subprocess adapter behind
the `exploration-graph` config toggle, so it stays swappable and independently
measurable per the architecture principle in MEMORY.md.

Real CLI (verified against v0.4.1):
  graphify-sf <path>                 build graph
  graphify-sf query "<q>" --budget N BFS traversal within a token budget
  graphify-sf path "<A>" "<B>"       shortest path
  graphify-sf explain "<node>"       node details + neighbors
  graphify-sf stats | serve (MCP)    stats / MCP stdio server
"""

import re
import shutil
import subprocess
import time
from typing import List, Optional

from . import metering, state, store

TESTED_VERSION = "0.4.1"
DEFAULT_BUDGET = "2000"

INACTIVE_EXIT = 3
DISABLED_EXIT = 4
NOT_FOUND_EXIT = 5

INACTIVE_MSG = (
    "[sfc] inactive - `sfc graph` needs an active dev session. Activate with: sfc on"
)
DISABLED_MSG = (
    "[sfc] exploration-graph is OFF. Enable it to use sfc graph:\n"
    '  set "exploration-graph": true in .sfc/config.json'
)
INSTALL_HINT = (
    "[sfc] graphify-sf not found. Install it (needs Python 3.10+):\n"
    "  pipx install graphify-sf=={v}\n"
    "  # or: uv tool install graphify-sf=={v}\n"
    "  # or: pip install graphify-sf=={v}\n"
    "Then build a graph once (graphify-sf <sfdx-path>) and query via:\n"
    '  sfc graph query "where is AccountTrigger used?"'
).format(v=TESTED_VERSION)


def resolve() -> Optional[List[str]]:
    """Return the base argv to invoke graphify-sf, or None if unavailable.

    Prefers a graphify-sf already on PATH; falls back to uvx/pipx launchers
    (which fetch on demand) so the pinned version is used without a manual install.
    """
    exe = shutil.which("graphify-sf")
    if exe:
        return [exe]
    if shutil.which("uvx"):
        return ["uvx", "--from", "graphify-sf=={}".format(TESTED_VERSION), "graphify-sf"]
    if shutil.which("pipx"):
        return ["pipx", "run", "--spec", "graphify-sf=={}".format(TESTED_VERSION),
                "graphify-sf"]
    return None


def probe_version(base: List[str]) -> Optional[str]:
    try:
        r = subprocess.run(base + ["--version"], capture_output=True, text=True,
                           timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    m = re.search(r"v?(\d+\.\d+\.\d+)", (r.stdout or "") + (r.stderr or ""))
    return m.group(1) if m else None


def run(argv: List[str], root=None) -> int:
    if not state.is_active(root):
        print(INACTIVE_MSG)
        return INACTIVE_EXIT
    config = state.load_config(root)
    if not config.get("exploration-graph", False):
        print(DISABLED_MSG)
        return DISABLED_EXIT

    base = resolve()
    if base is None:
        print(INSTALL_HINT)
        return NOT_FOUND_EXIT

    # version warning only for a PATH binary (probing a launcher would fetch it)
    if len(base) == 1:
        ver = probe_version(base)
        if ver and not ver.startswith("0.4"):
            print("[sfc] warning: graphify-sf {} detected; sfc was tested against "
                  "{}. Behavior may differ.".format(ver, TESTED_VERSION))

    args = list(argv)
    # default token budget for queries so exploration stays context-bounded
    if args and args[0] == "query" and "--budget" not in args:
        args = args + ["--budget", DEFAULT_BUDGET]

    cwd = str(root or state.find_root())
    start = time.time()
    try:
        proc = subprocess.run(base + args, cwd=cwd, capture_output=True, text=True,
                              errors="replace")
    except FileNotFoundError as exc:
        print("[sfc] failed to launch graphify-sf: {}".format(exc))
        return NOT_FOUND_EXIT
    duration = time.time() - start

    out = proc.stdout or ""
    if proc.stderr:
        out += ("\n" if out and not out.endswith("\n") else "") + proc.stderr
    if out:
        print(out, end="" if out.endswith("\n") else "\n")

    # meter as its own family (raw == emitted; the real win is avoided full reads)
    metering.log_call("graphify-sf " + " ".join(argv), "graph", store.new_id(),
                      len(out), len(out), None, proc.returncode, duration, root)
    return proc.returncode
