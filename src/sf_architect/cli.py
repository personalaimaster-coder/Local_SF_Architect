"""CLI entrypoint for sf-local-architect."""

from __future__ import annotations

import sys

import click

from sf_architect import __version__
from sf_architect.bootstrap import SF_ARCHITECT_HOME, ensure_data_dirs


@click.group()
@click.version_option(__version__, prog_name="sf-architect")
def main() -> None:
    """Local Salesforce architect tooling."""


@main.command()
def doctor() -> None:
    """Check Python version and local data directories."""
    py_ok = sys.version_info >= (3, 12)
    click.echo(f"Python: {sys.version} ({'ok' if py_ok else 'requires >=3.12'})")

    home = ensure_data_dirs()
    click.echo(f"Data home: {home} ({'ok' if home == SF_ARCHITECT_HOME else 'unexpected'})")
    click.echo(f"  data/: {'ok' if (home / 'data').is_dir() else 'missing'}")
    click.echo(f"  logs/: {'ok' if (home / 'logs').is_dir() else 'missing'}")
    click.echo(f"  config.yaml: {'ok' if (home / 'config.yaml').is_file() else 'missing'}")

    if not py_ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
