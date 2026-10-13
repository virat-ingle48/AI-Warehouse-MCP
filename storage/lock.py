import sys
from pathlib import Path
from typing import IO, Optional

DEFAULT_LOCK_FILE = Path(__file__).parent.parent / "server.lock"

_lock_handle: Optional[IO] = None


def acquire_singleton_lock(lock_file: Path = DEFAULT_LOCK_FILE) -> bool:
    global _lock_handle
    handle = open(lock_file, "w")

    try:
        if sys.platform == "win32":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return False

    _lock_handle = handle
    return True


def release_singleton_lock() -> None:
    global _lock_handle
    if _lock_handle is not None:
        _lock_handle.close()
        _lock_handle = None