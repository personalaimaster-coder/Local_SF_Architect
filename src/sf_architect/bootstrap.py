"""Bootstrap local data directories under ~/.sf-architect/."""

from __future__ import annotations

from pathlib import Path

SF_ARCHITECT_HOME = Path.home() / ".sf-architect"
DATA_DIR = SF_ARCHITECT_HOME / "data"
LOGS_DIR = SF_ARCHITECT_HOME / "logs"
CONFIG_PATH = SF_ARCHITECT_HOME / "config.yaml"

DEFAULT_CONFIG = """\
# sf-local-architect configuration
deliverable_preference: mermaid
embedding_model: BAAI/bge-small-en-v1.5
"""


def ensure_data_dirs() -> Path:
    """Create ~/.sf-architect data and log directories; write default config if missing."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(DEFAULT_CONFIG, encoding="utf-8")
    return SF_ARCHITECT_HOME
