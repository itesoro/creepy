import os
import time
import signal
import multiprocessing
from threading import Thread

import pytest

from ..processify import processify


def test_processify_big_o_1():
    for i in range(100):
        assert i == processify(lambda: i)()


def test_processify_crash():
    for i in range(2):
        with pytest.raises(RuntimeError, match=f'exited with code {i}'):
            processify(quit)(i)


def test_processify_parent_crash():
    q = multiprocessing.Queue()

    @processify
    def child():
        q.put(os.getpid())
        time.sleep(100500)

    @processify
    def parent():
        Thread(target=child, daemon=True).start()
        time.sleep(0.1)  # wait a bit so child can enqueue its `pid`
        os.kill(os.getpid(), signal.SIGKILL)  # suicide

    with pytest.raises(RuntimeError, match=f'exited with code -{signal.SIGKILL}'):
        parent()

    child_pid = q.get()
    handler = signal.signal(signal.SIGALRM, lambda: 0 / 0)
    try:
        signal.alarm(1)
        with pytest.raises(ChildProcessError, match="No child processes"):
            os.waitpid(child_pid, 0)
    finally:
        signal.signal(signal.SIGALRM, handler)
        signal.alarm(0)