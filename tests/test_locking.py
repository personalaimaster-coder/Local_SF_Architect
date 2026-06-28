"""Single-writer locking: mutual exclusion and serialized writes."""

import threading
import time

from sf_architect.locking import write_lock


def test_lock_serializes_writers() -> None:
    order = []

    def worker(label, hold):
        with write_lock("test-lock", timeout=10):
            order.append(f"{label}-start")
            time.sleep(hold)
            order.append(f"{label}-end")

    t1 = threading.Thread(target=worker, args=("a", 0.3))
    t2 = threading.Thread(target=worker, args=("b", 0.0))
    t1.start()
    time.sleep(0.05)  # ensure t1 grabs the lock first
    t2.start()
    t1.join()
    t2.join()

    # Whoever starts first must fully finish before the other starts.
    assert order in (
        ["a-start", "a-end", "b-start", "b-end"],
        ["b-start", "b-end", "a-start", "a-end"],
    )


def test_lock_reentrant_after_release() -> None:
    with write_lock("test-lock-2", timeout=5):
        pass
    # A second acquisition after release must succeed without timing out.
    with write_lock("test-lock-2", timeout=5):
        assert True
