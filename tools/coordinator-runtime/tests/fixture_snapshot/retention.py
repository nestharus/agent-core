"""Owned test substrate implementing only the selected snapshot_lock interface."""
from contextlib import contextmanager
from pathlib import Path
import fcntl
import os
import tempfile

CONTROL_DIR=Path(tempfile.gettempdir())/'coordinator-runtime-owned-fixture-lock'

@contextmanager
def snapshot_lock():
    CONTROL_DIR.mkdir(mode=0o700,exist_ok=True)
    fd=os.open(CONTROL_DIR/'work-rollback.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        yield
    finally:os.close(fd)
