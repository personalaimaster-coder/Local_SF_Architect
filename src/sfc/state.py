"""Project-local activation state and configuration.

Everything lives under `.sfc/` at the project root:
  state.json   {"active": bool}          -- the on/off gate (default ON)
  config.json  per-family filter toggles -- created with defaults on first `sfc on`

sfc is a dev-support tool. It is ON by default, so `sfc run` compresses output
out of the box. Running `sfc off` makes it fully dormant: `sfc run` refuses to
execute, nothing is stored, nothing is metered.
"""

import json
import os
from pathlib import Path
from typing import Optional

SFC_DIRNAME = ".sfc"

# sfc ships ON by default: when no explicit state.json exists we treat the tool as
# active. Running `sfc off` writes {"active": false} to opt out for a project.
DEFAULT_ACTIVE = True

DEFAULT_CONFIG = {
    "filters": {
        # per-family toggles (Pillar A families). True = compress, False = pass through raw.
        "sf-deploy": True,
        "sf-apex-test": True,
        "sf-debug-log": True,
        "sf-json": True,
        "sf-table": True,
        # behavior toggle (not a family): emit deploy-retry deltas vs the previous
        # run of the same command instead of a full report. Requires sf-deploy on.
        "deltas": True,
    },
    "store": {
        # keep the N most recent full raw outputs under .sfc/outputs/
        "retention": 50,
    },
    # reserved for Phase 2 modules (kept here so toggles are stable across versions)
    "exploration-graph": False,   # graphify-sf integration
    "dx-mcp-routing": False,      # Salesforce DX MCP Server routing
}


def find_root(start: Optional[str] = None) -> Path:
    """Project root = nearest ancestor (incl. cwd) containing .sfc/ or .git/; else cwd."""
    p = Path(start or os.getcwd()).resolve()
    for d in [p] + list(p.parents):
        if (d / SFC_DIRNAME).is_dir() or (d / ".git").exists():
            return d
    return p


def sfc_dir(root: Optional[Path] = None) -> Path:
    return (root or find_root()) / SFC_DIRNAME


def _read_json(path: Path, default):
    try:
        with open(path, "r") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def _write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as fh:
        json.dump(obj, fh, indent=2)
        fh.write("\n")


def is_active(root: Optional[Path] = None) -> bool:
    return bool(_read_json(sfc_dir(root) / "state.json", {}).get("active", DEFAULT_ACTIVE))


def _seed_gitignore(d: Path) -> None:
    # keep .sfc out of the host project's git status
    gitignore = d / ".gitignore"
    if not gitignore.exists():
        try:
            gitignore.write_text("*\n")
        except OSError:
            pass


def ensure_config(root: Optional[Path] = None) -> Path:
    """Create `.sfc/` with default config (idempotent) without writing state.json.

    Used by `sfc setup` to wire everything up. Because sfc is ON by default,
    leaving state.json unwritten means the tool is active unless the user runs
    `sfc off`. Returns the config.json path.
    """
    d = sfc_dir(root)
    cfg = d / "config.json"
    if not cfg.exists():
        _write_json(cfg, DEFAULT_CONFIG)
    _seed_gitignore(d)
    return cfg


def set_active(active: bool, root: Optional[Path] = None) -> None:
    d = sfc_dir(root)
    _write_json(d / "state.json", {"active": bool(active)})
    # seed config with defaults on first activation so toggles are discoverable
    if active and not (d / "config.json").exists():
        _write_json(d / "config.json", DEFAULT_CONFIG)
    _seed_gitignore(d)


def load_config(root: Optional[Path] = None) -> dict:
    """Defaults overlaid with whatever the user has in config.json."""
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))  # deep copy
    user = _read_json(sfc_dir(root) / "config.json", {})
    for key, val in user.items():
        if isinstance(val, dict) and isinstance(cfg.get(key), dict):
            cfg[key].update(val)
        else:
            cfg[key] = val
    return cfg


def filter_enabled(family: str, config: dict) -> bool:
    return bool(config.get("filters", {}).get(family, False))
