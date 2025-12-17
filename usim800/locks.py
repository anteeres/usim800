"""
Thread and Process Locking for SIM800

Provides combined thread-safe and process-safe locking to prevent
concurrent access to the serial port from multiple threads or processes.
"""
from __future__ import annotations
import os
import threading
from contextlib import contextmanager

try:
    import fcntl  # POSIX only (Linux, RPi)
except ImportError:  # pragma: no cover
    fcntl = None


class CombinedLock:
    """
    Combined thread lock + process lock.
    
    Thread lock: Always available (threading.RLock)
    Process lock: Uses flock() when available (Linux/RPi typical)
    """
    
    def __init__(self, lockfile: str | None = "/tmp/usim800.lock"):
        self._tlock = threading.RLock()
        self._lockfile = lockfile
        self._fd = None
    
    @contextmanager
    def acquire(self):
        """
        Acquire both thread and process locks.
        
        Usage:
            with lock.acquire():
                # Critical section
                pass
        """
        with self._tlock:
            if self._lockfile and fcntl is not None:
                # Acquire process lock
                self._fd = os.open(self._lockfile, os.O_CREAT | os.O_RDWR, 0o666)
                fcntl.flock(self._fd, fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(self._fd, fcntl.LOCK_UN)
                    os.close(self._fd)
                    self._fd = None
            else:
                # Thread lock only (Windows or no fcntl)
                yield
