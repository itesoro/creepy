import os
import time
import signal
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from threading import Thread

import psutil
import pytest

from ..processify import processify


def test_processify_on_simple_function():
    for i in range(100):
        assert i == processify(lambda: i)()


def test_processify_child_crash():
    for i in range(2):
        with pytest.raises(RuntimeError, match=f'exited with code {i}'):
            processify(quit)(i)


# Turn the warning into an error to verify that `processify` suppresses its intentional `fork`.
@pytest.mark.timeout(1)
@pytest.mark.filterwarnings('error:This process .* is multi-threaded:DeprecationWarning')
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
        time.sleep(0.5)
        assert not psutil.pid_exists(child_pid)
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

    time.sleep(0.1)
    assert not psutil.pid_exists(child_pids[0])


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
    time.sleep(0.1)
    assert not psutil.pid_exists(child_pid)
