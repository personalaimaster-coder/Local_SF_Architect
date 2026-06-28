"""Scrape allowlist + provenance enforcement (plan Gap 5, P0).

Scraping is disabled by default: ``scrape_allowlist`` in config is empty, so no
domain is permitted until the user explicitly adds one. This is the hard gate that
must exist before any scraping (Phase 3) is enabled.
"""

from __future__ import annotations

from urllib.parse import urlparse

from sf_architect.bootstrap import read_config


class DomainNotAllowedError(Exception):
    """Raised when a URL's domain is not in the configured allowlist."""


def _domain(url: str) -> str:
    return urlparse(url).netloc.lower()


def is_allowed(url: str, config: dict | None = None) -> bool:
    """True only if the URL's domain is in ``scrape_allowlist``."""
    config = config if config is not None else read_config()
    allowlist = {d.lower() for d in (config.get("scrape_allowlist") or [])}
    domain = _domain(url)
    if not domain:
        return False
    return any(domain == allowed or domain.endswith("." + allowed) for allowed in allowlist)


def require_allowed(url: str, config: dict | None = None) -> None:
    """Raise :class:`DomainNotAllowedError` if the URL is not allowlisted."""
    if not is_allowed(url, config):
        raise DomainNotAllowedError(
            f"domain for '{url}' is not in scrape_allowlist (scraping disabled by default)"
        )
