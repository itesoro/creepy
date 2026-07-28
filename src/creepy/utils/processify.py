import os
import signal
import warnings
import functools
import multiprocessing
from multiprocessing.connection import Connection as PipeConnection
from threading import Thread
from typing import Callable, Optional


def processify(fn=None, *, context='fork'):
    """
    Decorate `fn` to run it in a separate process.

    Parameters
    ----------
    fn : Callable
        Function to decorate.
    context : str, multiprocessing context, or None
        Multiprocessing context or start method. Uses `fork` by default; `None` selects the application default.

    Note
    ----
    It doesn't encrypt communications with a child process.
    The default `fork` context supports local and decorated functions independently of the application context.
    `spawn` and `forkserver` use their standard multiprocessing import and serialization rules.
    Results and exceptions must be pickleable in every context.
    Results must not depend on the worker remaining alive after they are deserialized.
    Functions using `fork` must not use inherited mutable global state or synchronization primitives.
    """
    if fn is None:
        return functools.partial(processify, context=context)

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        process_context = _get_process_context(context)
        in_connection, out_connection = process_context.Pipe(duplex=False)
        job_process = None
        try:
            # Block SIGINT in the calling thread to narrow the startup race until `start()` stores the child PID.
            # A signal delivered to another thread can still interrupt startup because POSIX masks are thread-local.
            previous_signal_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT})
            try:
                # With decorator syntax, spawn-like contexts resolve `wrapper` by module and qualified name.
                # Passing it under `fork` too keeps one child path; `_job` removes only the `processify` layer.
                job_process = process_context.Process(
                    target=_job,
                    args=(
                        in_connection, out_connection, wrapper, args, kwargs, previous_signal_mask,
                    ),
                )
                with warnings.catch_warnings():
                    # Python 3.12+ warns when the `fork` backend is used from a multithreaded process.
                    # Suppress that expected warning only during worker startup.
                    warnings.filterwarnings(
                        'ignore',
                        category=DeprecationWarning,
                        # Warning filters are process-wide on regular CPython, so restrict suppression to the `fork`
                        # backend.
                        module=r'multiprocessing\.popen_fork',
                    )
                    job_process.start()
                out_connection.close()
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, previous_signal_mask)
        except BaseException:
            in_connection.close()
            out_connection.close()
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


def _suicide_when_orphan():
    """Kill this process with SIGKILL signal when its logical parent exits."""
    # Under `forkserver`, the OS parent is the fork server; multiprocessing tracks the caller through a sentinel.
    parent_process = multiprocessing.parent_process()
    assert parent_process is not None
    parent_process.join()
    os.kill(os.getpid(), signal.SIGKILL)  # suicide


def _kill_join(process: Optional[multiprocessing.Process], *, wait=False):
    """Kill and join `process` if it was started, optionally waiting for completion."""
    if process is None or process.pid is None:
        return
    if process.exitcode is None:
        # POSIX multiprocessing backends tolerate the worker exiting between this poll and `kill()`.
        process.kill()
    if wait:
        process.join()
    else:
        Thread(target=process.join, daemon=True).start()


def _job(
        in_connection: PipeConnection, out_connection: PipeConnection, wrapper: Callable,
        args: tuple, kwargs: dict, signal_mask,
):
    # The worker only writes the response, so close its unused read end.
    in_connection.close()
    # Undo the parent's startup-only SIGINT block before running user code.
    signal.pthread_sigmask(signal.SIG_SETMASK, signal_mask)
    Thread(target=_suicide_when_orphan, daemon=True).start()
    # `functools.wraps` stores the callable passed to `processify`, so only this decorator layer is bypassed.
    fn = wrapper.__wrapped__
    try:
        result = (fn(*args, **kwargs), None)
    except Exception as e:
        result = (None, e)
    try:
        out_connection.send(result)
    finally:
        out_connection.close()


def _get_process_context(context):
    if not isinstance(context, str) and context is not None:
        return context
    try:
        return multiprocessing.get_context(context)
    except ValueError:
        raise RuntimeError(
            f'processify requires platform support for the {context!r} multiprocessing start method',
        ) from None
