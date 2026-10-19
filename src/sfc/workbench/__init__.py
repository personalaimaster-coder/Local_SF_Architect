"""Portable org workbench (Phase 2).

Built and tested on any machine (offline, via shims), but *run by the user on a
machine with an authenticated Salesforce org* and shareable with others:

  sfc collect   re-collect real fixture outputs (apex test, deploy validate,
                retrieve preview, query, describe) into a corpus folder.
  sfc bench     benchmark raw CLI vs the Salesforce DX MCP server per family and
                write a token-comparison report.

Neither command touches project source or git state. Org-side steps in
`sfc collect` (test run, deploy validate) are gated behind --allow-org-writes.
See docs/org-workbench.md for the runbook.
"""

from . import bench, collect  # noqa: F401
