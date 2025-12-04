import os
import fcntl
import contextlib


@contextlib.contextmanager
def sim800_lock(lockfile="/tmp/usim800.lock"):
    fd = os.open(lockfile, os.O_CREAT | os.O_RDWR, 0o666)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
