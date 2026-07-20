import os
import time
import signal
import functools
import multiprocessing
from multiprocessing.connection import Connection as PipeConnection
from threading import Thread
from typing import Callable


def processify(fn):
    """
    Decorate `fn` to run it in a separate process.

    Note
    ----
    It doesn't encrypt communications with a child process.
    It uses `fork` to support local and decorated functions, so call it only from a single-threaded process.
    """
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        in_connection, out_connection = _process_context.Pipe(duplex=False)
        job_process = _process_context.Process(target=_job, args=(os.getpid(), out_connection, fn, args, kwargs))
        try:
            job_process.start()
        except Exception:
            in_connection.close()
            out_connection.close()
            raise
        out_connection.close()
        try:
            try:
                response = in_connection.recv()
            except EOFError:
                response = None
        finally:
            in_connection.close()
            job_process.join()
        if response is None:
            raise RuntimeError(f'Process running {fn} exited with code {job_process.exitcode}')
        result, exception = response
        if exception is not None:
            raise exception
        return result

    return wrapper


def _suicide_when_orphan(ppid: int):
    """Kill this process with SIGKILL signal if parent pid ≠ `ppid`."""
    while os.getppid() == ppid:
        time.sleep(1 / 4)
    os.kill(os.getpid(), signal.SIGKILL)  # suicide


def _job(ppid: int, out_connection: PipeConnection, fn: Callable, args: tuple, kwargs: dict):
    Thread(target=_suicide_when_orphan, args=(ppid,), daemon=True).start()
    try:
        result = (fn(*args, **kwargs), None)
    except Exception as e:
        result = (None, e)
    out_connection.send(result)


try:
    _process_context = multiprocessing.get_context('fork')
except ValueError:
    _process_context = multiprocessing.get_context()
