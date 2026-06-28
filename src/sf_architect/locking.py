"""Single-writer file locking (plan additional gap #1).

stdio MCP servers are spawned per session, so multiple IDE windows can launch
multiple processes that write the same LanceDB / SQLite files. This module
provides an advisory write lock to serialize those writes.

Uses ``fcntl`` on POSIX and ``msvcrt`` on Windows, falling back to atomic
lock-file creation if neither is available.
"""

from __future__ import annotations

import os
import time
from contextlib import contextmanager
from pathlib import Path

from sf_architect.bootstrap import SF_ARCHITECT_HOME

try:  # POSIX
    import fcntl

    _HAVE_FCNTL = True
except ImportError:  # pragma: no cover - platform dependent
    _HAVE_FCNTL = False

try:  # Windows
    import msvcrt

    _HAVE_MSVCRT = True
except ImportError:
    _HAVE_MSVCRT = False


class LockTimeout(Exception):
    """Raised when a write lock cannot be acquired within the timeout."""


def _lock_path(name: str) -> Path:
    locks_dir = SF_ARCHITECT_HOME / "locks"
    locks_dir.mkdir(parents=True, exist_ok=True)
    return locks_dir / f"{name}.lock"


@contextmanager
def write_lock(name: str = "stores", timeout: float = 30.0, poll: float = 0.1):
    """Acquire an exclusive advisory write lock named ``name``.

    Serializes writes to the shared stores. Raises :class:`LockTimeout` if the
    lock cannot be acquired within ``timeout`` seconds.
    """
    path = _lock_path(name)
    deadline = time.monotonic() + timeout

    if _HAVE_FCNTL:
        fh = open(path, "w")
        try:
            while True:
                try:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise LockTimeout(f"could not acquire lock '{name}' in {timeout}s")
                    time.sleep(poll)
            yield
        finally:
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            finally:
                fh.close()
        return

    if _HAVE_MSVCRT:  # pragma: no cover - exercised on Windows only
        fh = open(path, "w")
        try:
            while True:
                try:
                    msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise LockTimeout(f"could not acquire lock '{name}' in {timeout}s")
                    time.sleep(poll)
            yield
        finally:
            try:
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
            finally:
                fh.close()
        return

    # Fallback: atomic exclusive-create lock file (pragma: best effort).
    while True:
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            break
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise LockTimeout(f"could not acquire lock '{name}' in {timeout}s")
            time.sleep(poll)
    try:
        yield
    finally:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
