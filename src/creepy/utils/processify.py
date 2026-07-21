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
    It always uses `fork` to support local and decorated functions, independently of the application context.
    `fn` must not use inherited mutable global state or synchronization primitives.
    In multithreaded processes, SIGINT protection during worker startup is best-effort because signal masks are
    thread-local.
    """
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        process_context = _get_process_context()
        in_connection, out_connection = process_context.Pipe(duplex=False)
        job_process = None
        try:
            # Block SIGINT in the calling thread to narrow the startup race until `start()` stores the child PID.
            # A signal delivered to another thread can still interrupt startup because POSIX masks are thread-local.
            previous_signal_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT})
            try:
                job_process = process_context.Process(
                    target=_job,
                    args=(
                        os.getpid(), in_connection, out_connection, fn, args, kwargs, previous_signal_mask,
                    ),
                )
                # This scope is process-wide on regular CPython, so match only the expected `fork` warning.
                with warnings.catch_warnings():
                    warnings.filterwarnings(
                        'ignore',
                        message=(
                            r'This process .* is multi-threaded, use of fork\(\) may lead '
                            r'to deadlocks in the child\.'
                        ),
                        category=DeprecationWarning,
                        module=r'multiprocessing\.popen_fork',
                    )
                    job_process.start()
                out_connection.close()
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, previous_signal_mask)
        except BaseException:
            in_connection.close()
            out_connection.close()
            if job_process is not None and job_process.pid is not None:
                _kill_join(job_process)
            raise
        try:
            response = in_connection.recv()
        except EOFError:
            # Wait only after killing the worker so its exit code is available without waiting for its threads.
            _kill_join(job_process, wait=True)
            raise RuntimeError(f'Process running {fn} exited with code {job_process.exitcode}') from None
        except BaseException:
            _kill_join(job_process)
            raise
        else:
            # `recv()` returned a fully deserialized response, so the disposable worker is no longer needed.
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


def _kill_join(process: multiprocessing.Process, *, wait=False):
    """Kill `process` if it is running and join it, optionally waiting for completion."""
    if process.exitcode is None:
        # The worker may exit after this check; fork Popen.kill() tolerates that race.
        process.kill()
    if wait:
        process.join()
    else:
        Thread(target=process.join, daemon=True).start()


def _job(
        ppid: int, in_connection: PipeConnection, out_connection: PipeConnection,
        fn: Callable, args: tuple, kwargs: dict, signal_mask,
):
    # `fork` inherits both pipe ends, but the child only writes the response.
    in_connection.close()
    # Undo the parent's startup-only SIGINT block before running user code.
    signal.pthread_sigmask(signal.SIG_SETMASK, signal_mask)
    Thread(target=_suicide_when_orphan, args=(ppid,), daemon=True).start()
    try:
        result = (fn(*args, **kwargs), None)
    except Exception as e:
        result = (None, e)
    try:
        out_connection.send(result)
    finally:
        out_connection.close()


def _get_process_context():
    # Local and decorated functions cannot be serialized for `spawn` or `forkserver` by the standard pickler.
    try:
        return multiprocessing.get_context('fork')
    except ValueError:
        raise RuntimeError("processify requires platform support for the 'fork' multiprocessing start method") from None
