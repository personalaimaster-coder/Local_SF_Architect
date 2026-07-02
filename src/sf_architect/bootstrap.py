"""Bootstrap local data directories and metadata under ~/.sf-architect/."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

SF_ARCHITECT_HOME = Path.home() / ".sf-architect"
DATA_DIR = SF_ARCHITECT_HOME / "data"
LANCE_DIR = DATA_DIR / "lance"
LOGS_DIR = SF_ARCHITECT_HOME / "logs"
DIAGRAMS_DIR = SF_ARCHITECT_HOME / "diagrams"
CONFIG_PATH = SF_ARCHITECT_HOME / "config.yaml"
LIMITS_DB_PATH = SF_ARCHITECT_HOME / "limits.db"
AUDIT_DB_PATH = LOGS_DIR / "audit.db"
META_PATH = SF_ARCHITECT_HOME / "meta.json"
OVERRIDES_PATH = SF_ARCHITECT_HOME / "tenant_overrides.json"

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
VECTOR_DIM = 384
SCHEMA_VERSION = 1

DEFAULT_CONFIG = """\
# sf-local-architect configuration
deliverable_preference: mermaid          # mermaid | drawio
embedding_model: BAAI/bge-small-en-v1.5
reranker_enabled: false
reranker_model: BAAI/bge-reranker-v2-m3
source_trust:                            # per-domain overrides (Gap 3)
  help.salesforce.com: 100
  architect.salesforce.com: 95
  default: 60
scrape_allowlist: []                     # P0 for Gap 5; empty = scraping disabled
"""


def repo_data_dir() -> Path:
    """Locate the directory holding the seed sources (``limits_seed.yaml`` etc.).

    Resolution order:

    1. ``sf_architect/data/`` packaged alongside this module — present when the
       package is installed from a wheel (PyPI / ``uv tool install`` / ``uvx``),
       where the seed files are force-included at build time.
    2. The repo-root ``data/`` directory — present in a dev checkout.
    3. ``./data`` relative to the current working directory — last-resort fallback.

    The first candidate that actually contains ``limits_seed.yaml`` wins, so the
    same code path works whether running from source or from an installed wheel.
    """
    candidates = [
        Path(__file__).resolve().parent / "data",
        Path(__file__).resolve().parents[2] / "data",
        Path.cwd() / "data",
    ]
    for candidate in candidates:
        if (candidate / "limits_seed.yaml").exists():
            return candidate
    return candidates[0]


def default_meta() -> dict:
    """The metadata that guards embedding-model/dimension and schema version."""
    return {
        "embedding_model": EMBEDDING_MODEL,
        "vector_dim": VECTOR_DIM,
        "schema_version": SCHEMA_VERSION,
        "limits_last_verified": None,
    }


def ensure_data_dirs() -> Path:
    """Create the ~/.sf-architect layout, default config, and meta.json if missing."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LANCE_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(DEFAULT_CONFIG, encoding="utf-8")
    if not META_PATH.exists():
        write_meta(default_meta())
    return SF_ARCHITECT_HOME


def read_config(config_path: str | Path | None = None) -> dict:
    """Read config.yaml, falling back to the embedded defaults if absent."""
    path = Path(config_path) if config_path is not None else CONFIG_PATH
    if not path.exists():
        return yaml.safe_load(DEFAULT_CONFIG) or {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def write_config(config: dict, config_path: str | Path | None = None) -> None:
    """Persist config.yaml."""
    path = Path(config_path) if config_path is not None else CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")


def read_meta() -> dict:
    """Read meta.json, returning defaults if it does not exist yet."""
    if not META_PATH.exists():
        return default_meta()
    return json.loads(META_PATH.read_text(encoding="utf-8"))


def write_meta(meta: dict) -> None:
    """Persist meta.json."""
    META_PATH.parent.mkdir(parents=True, exist_ok=True)
    META_PATH.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def validate_meta() -> tuple[bool, str | None]:
    """Check stored metadata matches the active embedding model and dimensions.

    Returns ``(ok, message)``. A mismatch means the vector store was built with a
    different model/dimension and must be rebuilt before querying (prevents silent
    corruption; plan Section 12.6).
    """
    meta = read_meta()
    if meta.get("vector_dim") != VECTOR_DIM:
        return False, (
            f"vector_dim mismatch: stored={meta.get('vector_dim')} active={VECTOR_DIM}. "
            "Run 'sf-architect rebuild' to recreate the vector store."
        )
    if meta.get("embedding_model") != EMBEDDING_MODEL:
        return False, (
            f"embedding_model mismatch: stored={meta.get('embedding_model')} "
            f"active={EMBEDDING_MODEL}. Run 'sf-architect rebuild'."
        )
    return True, None
