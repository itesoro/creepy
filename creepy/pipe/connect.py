import os
import sys
import pickle
import hashlib
import inspect
import subprocess
from typing import Optional

from .common import Request, secure_alice, make_send, make_recv


class Session:
    def __init__(self, process, send, recv):
        self._process = process
        self._send, self._recv = secure_alice(send, recv)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._process.kill()

    def request(self, endpoint, *args, **kwargs):
        request = Request(endpoint, args, kwargs)
        self._send(pickle.dumps(request))
        response = pickle.loads(self._recv())
        if response.error is not None:
            raise response.error
        return response.result


# TODO(Roman Rizvanov): Some MITM attacks can be prevented by tamper detection techniques:
# - Examine handshake latency.
# - Make sure only one process is created.
# - Check LD_PRELOAD env variable isn't set.
def connect(filename: str, hash: Optional[str] = None) -> Session:
    """
    Parameters
    ----------
    filename: str
        File name of python module without '.py' extension.
    hash: str, optional
        Expected SHA256 hash of the module in hex format.

    Note
    ----
    Hash verification doesn't increase security: if an attacker can rewrite app's source code, he can as well
    change `hash` in client's source code. Even if you're sure sources are genuine, it's possible to hook python
    process creation and inject mallicious code at run-time.
    Using this function secures connection with child process once direct connection is established but doesn't protect
    against some man-in-the-middle attacks.
    """
    try:
        caller_dir = os.path.dirname(inspect.stack()[1].filename)
        filename = os.path.join(caller_dir, filename)
    except Exception:
        pass
    filename = filename + '.py'
    source_code = open(filename, 'rb').read()
    if hash is not None:
        actual_hash = hashlib.sha256(source_code).hexdigest()
        if actual_hash != hash:
            raise ValueError(f"Invalid hash: expected: {repr(hash)}: actual: {repr(actual_hash)}")
    args = [sys.executable, '-c', _loader_code]
    process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    send, recv = make_send(process.stdin), make_recv(process.stdout)
    # File with source code may change after hash was verified. To prevent running wrong code send correct code
    # to child process and execute it manually.
    send(filename.encode())
    send(source_code)
    return Session(process, send, recv)


_loader_code = """
import sys, struct
f = sys.stdin.buffer
h = struct.Struct('H')
def recv(): n, = h.unpack(f.read(h.size)); return f.read(n)
filename = recv().decode()
code_object = compile(recv(), filename, 'exec')
try:
    exec(code_object, {'__name__': '__main__', '__file__': filename})
except Ecxeption:
    import traceback
    traceback.print_exc()
""".strip()
