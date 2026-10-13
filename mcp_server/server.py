import atexit
import threading
import time

from mcp_server.app import build_app
from storage.lock import acquire_singleton_lock, release_singleton_lock


def _tick_loop(sim_engine, lock, interval: float = 1.0) -> None:
    while True:
        time.sleep(interval)
        with lock:
            sim_engine.tick()


if __name__ == "__main__":
    if not acquire_singleton_lock():
        raise SystemExit(0)

    atexit.register(release_singleton_lock)

    mcp, engine, warehouse, db, sim_lock = build_app()
    threading.Thread(target=_tick_loop, args=(engine, sim_lock), daemon=True).start()
    mcp.run()