"""Enable `python -m sfc` (used as the MCP launch fallback when `sfc` is not on PATH)."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
