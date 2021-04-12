import sys
import shlex
import pickle
import hashlib
import subprocess
from typing import Optional
from contextlib import contextmanager

from .common import Request, secure_alice, make_send, make_recv


class Session:
    def __init__(self, send, recv, source_code: Optional[bytes] = None):
        self._send, self._recv = secure_alice(send, recv)
        if source_code is not None:
            self._send(source_code)

    def request(self, endpoint, *args, **kwargs):
        request = Request(endpoint, args, kwargs)
        self._send(pickle.dumps(request))
        response = pickle.loads(self._recv())
        return response


_loader_code =  """
def _loader():
    import sys, struct
    f = sys.stdin.buffer
    h = struct.Struct('H')
    size_header = f.read(h.size)
    size, = h.unpack(size_header)
    source_code = f.read(size)
    globals().clear()
    exec(source_code.decode('utf8'))
_loader()
"""


# TODO(Roman Rizvanov): Some MITM attacks can be prevented by latency examination, tracking new processes, checking
# that LD_PRELOAD isn't set.
@contextmanager
def connect(args, *, hash: Optional[str] = None) -> Session:
    """
    Note
    ----
    Hash verification doesn't increase security: if an attacker can rewrite app's source code, he can as well
    change `hash` in client's source code. Even if you're sure sources are genuine, it's possible to hook python
    process creation and inject mallicious code at run-time.
    Using this function secures connection with child process once connection is established but doesn't protect
    against some man-in-the-middle attacks.
    """
    if isinstance(args, str):
        args = shlex.split(args)
    else:
        args = args.copy()
    args[0] = args[0] + '.py'
    if hash is not None:
        source_code = open(args[0], 'rb').read()
        actual_hash = hashlib.sha256(source_code).hexdigest()
        if actual_hash != hash:
            raise ValueError(f"Invalid hash: expected: {repr(hash)}: actual: {repr(actual_hash)}")
        args = [sys.executable, '-c', _loader_code] + args[1:]
    else:
        source_code = None
        args = [sys.executable] + args
    process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    try:
        send, recv = make_send(process.stdin), make_recv(process.stdout)
        if source_code is not None:
            send(source_code)
        yield Session(send, recv)
    finally:
        process.kill()
