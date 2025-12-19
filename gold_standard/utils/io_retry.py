"""Simple retry decorator for transient I/O operations.

Retries on OSError/IOError and sqlite3.OperationalError with exponential backoff.
"""
import time
import functools
import logging
import sqlite3
from typing import Callable

logger = logging.getLogger("io_retry")


def retry_on_ioerrors(max_retries: int = 5, initial_backoff: float = 0.5, max_backoff: float = 10.0):
    def decorator(fn: Callable):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            attempt = 0
            backoff = initial_backoff
            while True:
                try:
                    return fn(*args, **kwargs)
                except (OSError, IOError, sqlite3.OperationalError) as e:
                    attempt += 1
                    if attempt > max_retries:
                        logger.error(f"I/O retry exhausted for {fn.__name__}: {e}")
                        raise
                    logger.warning(f"I/O error in {fn.__name__}: {e} - retrying {attempt}/{max_retries} after {backoff}s")
                    time.sleep(backoff)
                    backoff = min(backoff * 2, max_backoff)

        return wrapper

    return decorator
