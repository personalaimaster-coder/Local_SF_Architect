"""Scrape allowlist: disabled by default; only configured domains allowed."""

import pytest

from sf_architect.security.allowlist import (
    DomainNotAllowedError,
    is_allowed,
    require_allowed,
)


def test_empty_allowlist_blocks_all() -> None:
    config = {"scrape_allowlist": []}
    assert is_allowed("https://help.salesforce.com/page", config) is False


def test_allowlisted_domain_permitted() -> None:
    config = {"scrape_allowlist": ["help.salesforce.com"]}
    assert is_allowed("https://help.salesforce.com/articleView", config) is True


def test_subdomain_of_allowlisted_permitted() -> None:
    config = {"scrape_allowlist": ["salesforce.com"]}
    assert is_allowed("https://architect.salesforce.com/x", config) is True


def test_non_allowlisted_refused() -> None:
    config = {"scrape_allowlist": ["help.salesforce.com"]}
    assert is_allowed("https://evil.example.com", config) is False
    with pytest.raises(DomainNotAllowedError):
        require_allowed("https://evil.example.com", config)
