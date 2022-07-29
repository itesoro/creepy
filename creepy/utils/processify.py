import os
import time
import signal
import struct
import functools
from multiprocessing import Process, Pipe
from multiprocessing.connection import Connection as PipeConnection
from threading import Thread
from typing import Callable


def processify(fn):
    """
    Decorator to run `fn` in a separate process.

    Note
    ----
    It doesn't encrypt communications with a child process.
    """
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        in_connection, out_connection = Pipe()
        job_process = Process(target=_job, args=(os.getpid(), out_connection, fn, args, kwargs))
        job_process.start()
        Thread(target=_join_close, args=(job_process, out_connection), daemon=True).start()
        try:
            result, exception = in_connection.recv()
        except struct.error:  # happens when `_join_close()` closes `out_fd`
            raise RuntimeError(f'Process running {fn} exited with code {job_process.exitcode}') from None
        if exception is not None:
            raise exception
        return result

    return wrapper


def _suicide_when_orphan(ppid: int):
    """Kill this process with SIGKILL signal if parent pid ≠ `ppid`."""
    while os.getppid() == ppid:
        time.sleep(1 / 4)
    os.kill(os.getpid(), signal.SIGKILL)  # suicide


def _join_close(process: Process, connection: PipeConnection):
    """Close file descriptor `fd` after `process` is done."""
    process.join()
    connection.close()


def _job(ppid: int, out_connection: PipeConnection, fn: Callable, args: tuple, kwargs: dict):
    Thread(target=_suicide_when_orphan, args=(ppid,), daemon=True).start()
    try:
        result = (fn(*args, **kwargs), None)
    except Exception as e:
        result = (None, e)
    out_connection.send(result)
