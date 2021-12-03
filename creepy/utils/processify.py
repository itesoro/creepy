import os
import time
import pickle
import signal
import struct
import functools
from creepy.subprocess import common as _common
from multiprocessing import Process
from threading import Thread


def processify(fn):
    """
    Decorator to run `fn` in a separate process.

    Note
    ----
    It doesn't encrypt communications with a child process.
    """
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        def job(ppid: int, out_fd: int):
            Thread(target=_suicide_when_orphan, args=(ppid,), daemon=True).start()
            send = _common.make_send(out_fd)
            try:
                result = (fn(*args, **kwargs), None)
            except Exception as e:
                result = (None, e)
            send(pickle.dumps(result))

        in_fd, out_fd = os.pipe()
        recv = _common.make_recv(in_fd)
        job_process = Process(target=job, args=(os.getpid(), out_fd), daemon=True)
        job_process.start()
        Thread(target=_join_close, args=(job_process, out_fd), daemon=True).start()
        try:
            result, exception = pickle.loads(recv())
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


def _join_close(process: Process, fd: int):
    """Close file descriptor `fd` after `process` is done."""
    process.join()
    os.close(fd)
