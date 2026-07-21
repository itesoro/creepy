import os
import time
import signal
import warnings
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
    It uses `fork` to support local and decorated functions, so `fn` must not use inherited global state.
    """
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        in_connection, out_connection = _process_context.Pipe(duplex=False)
        job_process = _process_context.Process(target=_job, args=(os.getpid(), out_connection, fn, args, kwargs))
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    'ignore',
                    message=r'This process .* is multi-threaded, use of fork\(\) may lead to deadlocks in the child\.',
                    category=DeprecationWarning,
                    module=r'multiprocessing\.popen_fork',
                )
                job_process.start()
            out_connection.close()
        except BaseException:
            in_connection.close()
            out_connection.close()
            if job_process.pid is not None:
                _kill_join(job_process)
            raise
        try:
            response = in_connection.recv()
        except EOFError:
            job_process.kill()
            job_process.join()
            raise RuntimeError(f'Process running {fn} exited with code {job_process.exitcode}') from None
        except BaseException:
            _kill_join(job_process)
            raise
        else:
            _kill_join(job_process)
        finally:
            in_connection.close()
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


def _kill_join(process: multiprocessing.Process):
    """Kill `process` and join it in background."""
    process.kill()
    Thread(target=process.join, daemon=True).start()


def _job(ppid: int, out_connection: PipeConnection, fn: Callable, args: tuple, kwargs: dict):
    Thread(target=_suicide_when_orphan, args=(ppid,), daemon=True).start()
    try:
        result = (fn(*args, **kwargs), None)
    except Exception as e:
        result = (None, e)
    try:
        out_connection.send(result)
    finally:
        out_connection.close()


_process_context = multiprocessing.get_context('fork')
