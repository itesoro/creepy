import os
import time
import functools
from concurrent import futures
from multiprocessing import Process, Queue

from creepy.memory import mlockall, MCL_FUTURE


def processify(fn, lock_memory=True):
    """
    Decorator to run `fn` in a separate process.

    Note
    ----
    It doesn't encrypt communications with a child process.
    """
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        q = Queue(maxsize=1)
        def job():
            def return_when_orphan():
                while True:
                    if os.getppid() == 1:
                        return
                    time.sleep(1 / 4)
            nonlocal fn
            if lock_memory:
                old_fn = fn
                def fn(*args, **kwargs):
                    mlockall(MCL_FUTURE)
                    return old_fn(*args, **kwargs)
            executor = futures.ThreadPoolExecutor(max_workers=2)
            when_orphan = executor.submit(return_when_orphan)
            when_result = executor.submit(fn, *args, **kwargs)
            futures.wait([when_orphan, when_result], return_when=futures.FIRST_COMPLETED)
            executor.shutdown(wait=False)
            try:
                q.put((when_result.result(), None))
            except Exception as ex:
                q.put((None, ex))
            q.close()
        p = Process(target=job)
        p.start()
        p.join()
        result, ex = q.get_nowait()
        if ex is not None:
            raise ex
        return result
    return wrapper
