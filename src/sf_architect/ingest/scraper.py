"""Web scraper (plan Phase 3 task 1).

Crawl4AI is an optional extra (``pip install sf-local-architect[scrape]``) because
it pulls in Playwright/Chromium (hundreds of MB). It is imported lazily so the
core package stays light and fully offline.

Scraping always runs behind the security gate: the allowlist is checked here, and
the caller runs sanitize + injection-guard before any write (see ``ingest.embed``).
"""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable
from urllib.parse import urlparse

from sf_architect.security.allowlist import require_allowed

Fetcher = Callable[[str], str]


class UnsafeUrlError(Exception):
    """Raised for non-http(s) schemes or SSRF-prone (private/loopback) targets."""


def validate_url(url: str) -> None:
    """Reject non-http(s) schemes and private/loopback/link-local targets (SSRF)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise UnsafeUrlError(f"unsupported scheme: {parsed.scheme!r}")
    host = parsed.hostname
    if not host:
        raise UnsafeUrlError("missing host")
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return  # unresolved host: allowlist still gates the actual fetch
    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise UnsafeUrlError(f"refusing SSRF-prone address {addr} for host {host}")


def _crawl4ai_fetch(url: str) -> str:  # pragma: no cover - requires [scrape] extra
    """Fetch a page and return clean markdown via Crawl4AI."""
    import asyncio

    from crawl4ai import AsyncWebCrawler

    async def run() -> str:
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)
            return result.markdown or ""

    return asyncio.run(run())


def fetch_markdown(
    url: str, fetcher: Fetcher | None = None, config: dict | None = None
) -> str:
    """Validate + allowlist-check a URL, then fetch it to clean markdown.

    ``fetcher`` is injectable so tests can supply fixture markdown without a live
    network or the heavy Crawl4AI dependency.
    """
    require_allowed(url, config)
    validate_url(url)
    fetcher = fetcher or _crawl4ai_fetch
    return fetcher(url)
