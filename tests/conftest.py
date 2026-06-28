"""Shared fixtures: seed temp LanceDB + limits.db from the repo seed files."""

from __future__ import annotations

from pathlib import Path

import pytest

from sf_architect.bootstrap import repo_data_dir

DATA_DIR = repo_data_dir()


@pytest.fixture(scope="session")
def seeded_lance(tmp_path_factory) -> Path:
    """A temp LanceDB directory loaded with the bundled seed patterns."""
    from sf_architect.engines.patterns import load_patterns_seed

    lance_dir = tmp_path_factory.mktemp("lance")
    load_patterns_seed(DATA_DIR / "patterns_seed.yaml", lance_dir=lance_dir)
    return lance_dir


@pytest.fixture(scope="session")
def seeded_limits(tmp_path_factory) -> Path:
    """A temp compiled limits.db built from the bundled seed."""
    from sf_architect.engines.limits import compile_seed

    db_path = tmp_path_factory.mktemp("limits") / "limits.db"
    compile_seed(DATA_DIR / "limits_seed.yaml", db_path=db_path)
    return db_path
