"""CLI entrypoint for sf-local-architect."""

from __future__ import annotations

import sys

import click
import yaml

from sf_architect import __version__
from sf_architect.bootstrap import (
    SF_ARCHITECT_HOME,
    ensure_data_dirs,
    read_meta,
    repo_data_dir,
    write_meta,
)


@click.group()
@click.version_option(__version__, prog_name="sf-architect")
def main() -> None:
    """Local Salesforce architect tooling."""


@main.command()
@click.option(
    "--download",
    is_flag=True,
    help="Pre-cache the embedding model for offline use (one-time online step).",
)
def doctor(download: bool) -> None:
    """Check Python version and local data directories."""
    py_ok = sys.version_info >= (3, 12)
    click.echo(f"Python: {sys.version} ({'ok' if py_ok else 'requires >=3.12'})")

    home = ensure_data_dirs()
    click.echo(f"Data home: {home} ({'ok' if home == SF_ARCHITECT_HOME else 'unexpected'})")
    click.echo(f"  data/: {'ok' if (home / 'data').is_dir() else 'missing'}")
    click.echo(f"  logs/: {'ok' if (home / 'logs').is_dir() else 'missing'}")
    click.echo(f"  config.yaml: {'ok' if (home / 'config.yaml').is_file() else 'missing'}")
    click.echo(f"  meta.json: {'ok' if (home / 'meta.json').is_file() else 'missing'}")

    if download:
        click.echo("Downloading / warming embedding model (this may take a minute)...")
        from sf_architect.engines.patterns import embed

        embed("warmup")
        click.echo("  embedding model: cached")

        # Pre-cache the cross-encoder too when reranking is enabled, so the engine
        # stays fully offline after setup (reranking otherwise downloads on first use).
        from sf_architect.bootstrap import read_config

        if read_config().get("reranker_enabled", False):
            click.echo("Downloading / warming reranker model...")
            try:
                from sf_architect.rerank import _default_scorer

                _default_scorer("warmup", ["warmup"])
                click.echo("  reranker model: cached")
            except Exception as exc:  # non-fatal: reranking degrades gracefully
                click.echo(f"  reranker model: skipped ({exc})")

    if not py_ok:
        raise SystemExit(1)


@main.command()
def seed() -> None:
    """(Re)load curated governor limits and bundled patterns into local stores."""
    ensure_data_dirs()
    from sf_architect.engines.limits import compile_seed
    from sf_architect.engines.patterns import load_patterns_seed

    data_dir = repo_data_dir()
    limits_seed = data_dir / "limits_seed.yaml"
    patterns_seed = data_dir / "patterns_seed.yaml"

    db_path = compile_seed(limits_seed)
    click.echo(f"Compiled governor limits -> {db_path}")

    count = load_patterns_seed(patterns_seed)
    click.echo(f"Loaded {count} patterns into LanceDB")

    seed_data = yaml.safe_load(limits_seed.read_text(encoding="utf-8")) or {}
    last_verified = None
    for payload in (seed_data.get("api_versions") or {}).values():
        lv = payload.get("last_verified")
        if lv and (last_verified is None or str(lv) > last_verified):
            last_verified = str(lv)
    meta = read_meta()
    meta["limits_last_verified"] = last_verified
    write_meta(meta)
    click.echo("Seed complete.")


@main.command()
def rebuild() -> None:
    """Drop and rebuild local stores from seed (safe path on schema changes)."""
    ensure_data_dirs()
    from sf_architect.bootstrap import SCHEMA_VERSION
    from sf_architect.engines.limits import compile_seed
    from sf_architect.engines.patterns import load_patterns_seed

    data_dir = repo_data_dir()
    compile_seed(data_dir / "limits_seed.yaml")
    count = load_patterns_seed(data_dir / "patterns_seed.yaml")
    meta = read_meta()
    meta["schema_version"] = SCHEMA_VERSION
    write_meta(meta)
    click.echo(f"Rebuilt stores; loaded {count} patterns; schema_version={SCHEMA_VERSION}.")


@main.command()
def gc() -> None:
    """Garbage-collect superseded (non-current) vectors from LanceDB."""
    ensure_data_dirs()
    from sf_architect.engines.patterns import gc_stale

    removed = gc_stale()
    click.echo(f"Removed {removed} stale vector(s).")


@main.command(name="test")
def test_cmd() -> None:
    """Run the test suite (contract, embedding, golden-set, parser checks)."""
    try:
        import pytest
    except ImportError:
        click.echo("pytest not installed; install the dev group: uv sync")
        raise SystemExit(2) from None

    repo_root = repo_data_dir().parent
    raise SystemExit(pytest.main([str(repo_root / "tests"), "-q"]))


@main.command()
@click.argument("path", type=click.Path(exists=True), default=".")
def score(path: str) -> None:
    """Print an explainable per-pillar architecture scorecard for PATH."""
    from sf_architect.engines.scoring import score_architecture

    result = score_architecture(path)
    for pillar, card in result["pillars"].items():
        click.echo(f"{pillar}: {card['score']}/100 ({len(card['findings'])} finding(s))")
    click.echo(f"risk_score: {result['risk_score']}")


@main.command()
@click.argument("path", type=click.Path(exists=True), default=".")
def lint(path: str) -> None:
    """Scan Apex for architectural infractions (non-zero exit on findings)."""
    from sf_architect.lint import scan_path

    infractions = scan_path(path)
    for infraction in infractions:
        click.echo(
            f"{infraction.file}:{infraction.line} "
            f"[{infraction.pillar}/{infraction.rule}] {infraction.message}"
        )
    if infractions:
        click.echo(f"{len(infractions)} infraction(s) found.")
        raise SystemExit(1)
    click.echo("No architectural infractions found.")


if __name__ == "__main__":
    main()
