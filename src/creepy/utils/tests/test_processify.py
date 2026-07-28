import os
import time
import signal
import functools
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from threading import Thread

import psutil
import pytest

from ..processify import processify


def test_processify_on_simple_function():
    for i in range(100):
        assert i == processify(lambda: i)()


def test_processify_fork_accepts_unpickleable_argument():
    @processify
    def call(fn):
        return fn()

    assert call(lambda: 42) == 42


def test_processify_as_decorator_factory():
    @processify()
    def add(a, b):
        return a + b

    assert add(1, 2) == 3


def test_processify_preserves_existing_decorator():
    @_double_result
    def identity(value):
        return value

    assert processify(identity)(21) == 42


@pytest.mark.parametrize('method', ('spawn', 'forkserver'))
def test_processify_with_non_fork_context(method):
    if method not in multiprocessing.get_all_start_methods():
        pytest.skip(f'{method} start method is unavailable')
    assert _WORKERS[method](21) == 42


def test_processify_method_with_spawn_context():
    assert _Processified().add(1, 2) == 3


@pytest.mark.timeout(10)
@pytest.mark.parametrize('method', ('spawn', 'forkserver'))
def test_processify_orphan_with_non_fork_context(method):
    if method not in multiprocessing.get_all_start_methods():
        pytest.skip(f'{method} start method is unavailable')
    worker = _ORPHAN_WORKERS[method]
    child_in_connection, child_out_connection = multiprocessing.Pipe(duplex=False)
    crash_in_connection, crash_out_connection = multiprocessing.Pipe(duplex=False)
    parent = multiprocessing.get_context('spawn').Process(
        target=_crash_processified_parent,
        args=(worker, child_out_connection, crash_in_connection),
    )
    child_process = None
    with child_in_connection, child_out_connection, crash_in_connection, crash_out_connection:
        try:
            parent.start()
            child_out_connection.close()
            crash_in_connection.close()
            child_pid = child_in_connection.recv()
            child_process = psutil.Process(child_pid)
            crash_out_connection.send(None)
            parent.join()
            assert parent.exitcode == -signal.SIGKILL
            _assert_process_exits(child_pid, timeout=5)
        finally:
            if parent.pid is not None:
                if parent.is_alive():
                    parent.kill()
                parent.join()
            if child_process is not None:
                try:
                    child_process.kill()
                except psutil.NoSuchProcess:
                    pass


def test_processify_with_context_selection():
    assert _spawn_context_worker() == 42
    assert _application_context_worker() == multiprocessing.get_start_method()


def test_processify_without_fork(monkeypatch):
    def get_context(method):
        assert method == 'fork'
        raise ValueError

    monkeypatch.setattr(multiprocessing, 'get_context', get_context)
    with pytest.raises(RuntimeError, match="requires platform support for the 'fork'"):
        processify(lambda: None)()


@pytest.mark.parametrize('exitcode', (0, 1))
def test_processify_child_crash(exitcode):
    with pytest.raises(RuntimeError, match=f'exited with code {exitcode}'):
        processify(quit)(exitcode)


@pytest.mark.timeout(1)
# Fail on any deprecation warning so changes to the intentional `fork` warning cannot bypass this test.
@pytest.mark.filterwarnings('error::DeprecationWarning')
def test_processify_parent_crash():
    connection = multiprocessing.Queue()

    @processify
    def child():
        connection.put(os.getpid())
        time.sleep(100500)

    @processify
    def parent():
        Thread(target=child, daemon=True).start()
        time.sleep(0.1)  # wait a bit for child to enqueue its `pid`
        os.kill(os.getpid(), signal.SIGKILL)  # suicide

    with ThreadPoolExecutor() as executor:
        parent_future = executor.submit(parent)
        child_pid = connection.get()
        assert psutil.pid_exists(child_pid)
        _assert_process_exits(child_pid)
        with pytest.raises(RuntimeError, match=f'exited with code -{signal.SIGKILL}'):
            parent_future.result()


@pytest.mark.timeout(1)
def test_processify_child_thread():
    @processify
    def child():
        Thread(target=time.sleep, args=(100500,)).start()

    child()


@pytest.mark.timeout(1)
def test_processify_unpickleable_result_with_child_thread():
    @processify
    def child():
        Thread(target=time.sleep, args=(100500,)).start()
        return lambda: None

    with pytest.raises(RuntimeError, match=f'exited with code -{signal.SIGKILL}'):
        child()


@pytest.mark.timeout(1)
def test_processify_interrupt_during_start(monkeypatch):
    child_pids = []
    popen = multiprocessing.context.ForkProcess._Popen

    def popen_and_interrupt(process):
        child_process = popen(process)
        child_pids.append(child_process.pid)
        os.kill(os.getpid(), signal.SIGINT)
        return child_process

    monkeypatch.setattr(multiprocessing.context.ForkProcess, '_Popen', staticmethod(popen_and_interrupt))
    with pytest.raises(KeyboardInterrupt):
        processify(time.sleep)(100500)

    _assert_process_exits(child_pids[0])


@pytest.mark.timeout(1)
def test_processify_interrupt_during_receive():
    connection = multiprocessing.Queue()
    parent_pid = os.getpid()

    @processify
    def child():
        connection.put(os.getpid())
        time.sleep(0.1)
        os.kill(parent_pid, signal.SIGINT)
        time.sleep(100500)

    with pytest.raises(KeyboardInterrupt):
        child()

    child_pid = connection.get(timeout=0.1)
    _assert_process_exits(child_pid)


def _double_result(fn):
    @functools.wraps(fn)
    def wrapper(value):
        return fn(value) * 2

    return wrapper


@processify(context='spawn')
@_double_result
def _spawn_worker(value):
    return value


@processify(context='forkserver')
@_double_result
def _forkserver_worker(value):
    return value


@processify(context=multiprocessing.get_context('spawn'))
def _spawn_context_worker():
    return 42


@processify(context=None)
def _application_context_worker():
    return multiprocessing.get_start_method()


class _Processified:
    @processify(context='spawn')
    def add(self, a, b):
        return a + b


@processify(context='spawn')
def _spawn_until_orphaned(connection):
    connection.send(os.getpid())
    time.sleep(100500)


@processify(context='forkserver')
def _forkserver_until_orphaned(connection):
    connection.send(os.getpid())
    time.sleep(100500)


_WORKERS = {
    'spawn': _spawn_worker,
    'forkserver': _forkserver_worker,
}

_ORPHAN_WORKERS = {
    'spawn': _spawn_until_orphaned,
    'forkserver': _forkserver_until_orphaned,
}


def _crash_processified_parent(worker, child_connection, crash_connection):
    Thread(target=worker, args=(child_connection,), daemon=True).start()
    crash_connection.recv()
    os.kill(os.getpid(), signal.SIGKILL)


def _assert_process_exits(pid, timeout=0.5):
    try:
        process = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return
    _, alive = psutil.wait_procs([process], timeout=timeout)
    # Do not leak the worker when the assertion fails.
    for process in alive:
        try:
            process.kill()
        except psutil.NoSuchProcess:
            pass
    assert not alive
