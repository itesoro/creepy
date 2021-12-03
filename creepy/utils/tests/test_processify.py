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


@pytest.mark.timeout(1)
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
