import os
import pickle
import signal
import warnings
import functools
import multiprocessing
from multiprocessing.connection import Connection as PipeConnection
from threading import Thread
from typing import Callable


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
    With `spawn` and `forkserver`, `fn` or its `processify` wrapper must be importable by module and qualified name.
    Arguments, results, and exceptions must be pickleable.
    Results must not depend on the worker remaining alive after they are deserialized.
    Functions using `fork` must not use inherited mutable global state or synchronization primitives.
    """
    if fn is None:
        return functools.partial(_processify, context=context)
    return _processify(fn, context=context)


def _processify(fn, *, context):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        process_context = _get_process_context(context)
        job_fn, unwrap_fn = _get_job_fn(process_context, fn, wrapper)
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
                        in_connection, out_connection, job_fn, unwrap_fn,
                        args, kwargs, previous_signal_mask,
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


def _suicide_when_orphan():
    """Kill this process with SIGKILL signal when its logical parent exits."""
    # Under `forkserver`, the OS parent is the fork server; multiprocessing tracks the caller through a sentinel.
    parent_process = multiprocessing.parent_process()
    assert parent_process is not None
    parent_process.join()
    os.kill(os.getpid(), signal.SIGKILL)  # suicide


def _kill_join(process: multiprocessing.Process, *, wait=False):
    """Kill `process` if it is running and join it, optionally waiting for completion."""
    if process.exitcode is None:
        # POSIX multiprocessing backends tolerate the worker exiting between this poll and `kill()`.
        process.kill()
    if wait:
        process.join()
    else:
        Thread(target=process.join, daemon=True).start()


def _job(
        in_connection: PipeConnection, out_connection: PipeConnection, fn: Callable,
        unwrap_fn: bool, args: tuple, kwargs: dict, signal_mask,
):
    # `fork` inherits both pipe ends, but the child only writes the response.
    in_connection.close()
    # Undo the parent's startup-only SIGINT block before running user code.
    signal.pthread_sigmask(signal.SIG_SETMASK, signal_mask)
    Thread(target=_suicide_when_orphan, daemon=True).start()
    if unwrap_fn:
        # `spawn` and `forkserver` can import the module-level wrapper; `__wrapped__` bypasses this decorator once.
        fn = fn.__wrapped__
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


def _get_job_fn(process_context, fn, wrapper):
    if process_context.get_start_method() == 'fork':
        return fn, False
    try:
        pickle.dumps(fn)
    except (pickle.PickleError, AttributeError, TypeError):
        try:
            pickle.dumps(wrapper)
        except (pickle.PickleError, AttributeError, TypeError):
            raise RuntimeError(
                f'processify using {process_context.get_start_method()!r} requires `fn` or its wrapper '
                'to be importable by module and qualified name',
            ) from None
        # The importable decorated name resolves to `wrapper`; the child bypasses this `processify` layer once.
        return wrapper, True
    return fn, False
