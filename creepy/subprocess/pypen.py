import os
import sys
import fcntl
import shlex
import pickle
import hashlib
import inspect
import secrets
import subprocess
from typing import Optional

from .common import Request, secure_alice, secure_channel, make_send, make_recv


# TODO(Roman Rizvanov): Some MITM attacks can be prevented by tamper detection techniques:
# - Examine handshake latency.
# - Make sure only one process is created.
# - Check LD_PRELOAD env variable isn't set.
class Pypen:
    def __init__(self, args, hash: Optional[str] = None, serializable: bool = False, **kwargs):
        """
        Parameters
        ----------
        args: str, List[str]
            Should be a sequence of python program arguments or else a single string. If `args` is a string it is
            splitted into sequence using `shlex.split(args)`. The program to execute is the first item in `args`,
            it should be specified without '.py' extension.  Unless otherwise stated, it is recommended to pass `args`
            as a sequence.
        hash: str, optional
            Expected SHA256 hash of the module in hex format.
        serializable: bool, optional
            When set the process can be serialized and passed to another process.

        Note
        ----
        Hash verification doesn't increase security: if an attacker can rewrite the program's source code, he can as
        well change `hash` in client's source code. Even if you're sure sources are genuine, it's possible to hook
        python process creation and inject mallicious code at run-time.
        Using this function secures connection with child process once direct connection is established but doesn't protect
        against some man-in-the-middle attacks.
        """
        if isinstance(args, str):
            args = shlex.split(args)
        try:
            filename = args[0]
        except IndexError:
            raise ValueError('`args` is invalid') from None
        try:
            caller_dir = os.path.dirname(inspect.stack()[1].filename)
            filename = os.path.join(caller_dir, filename)
        except Exception:
            pass
        filename = filename + '.py'
        with open(filename, 'rb') as f:
            source_code = f.read()
        if hash is not None:
            actual_hash = hashlib.sha256(source_code).hexdigest()
            if actual_hash != hash:
                raise ValueError(f"Invalid hash: expected: {repr(hash)}: actual: {repr(actual_hash)}")
        if serializable:
            child_in_fd, parent_out_fd, self._out_path = _make_fifo()
            parent_in_fd, child_out_fd, self._in_path = _make_fifo()
        else:
            child_in_fd, parent_out_fd = os.pipe()
            parent_in_fd, child_out_fd = os.pipe()
        self._fds = (child_in_fd, parent_out_fd, parent_in_fd, child_out_fd)
        args[0] = filename
        loader_code = _loader_code_template.format(
            args=args,
            fdr=child_in_fd,
            fdw=child_out_fd
        )
        args = [sys.executable, '-c', loader_code]
        kwargs['pass_fds'] = kwargs.get('pass_fds', ()) + (child_in_fd, child_out_fd)
        self._process = subprocess.Popen(args, **kwargs)
        send, recv = make_send(parent_out_fd), make_recv(parent_in_fd)
        send(source_code)
        try:
            self._cipher_name, self._symmetric_key = secure_alice(send, recv)
            self._send, self._recv = secure_channel(send, recv, self._cipher_name, self._symmetric_key)
        except Exception:
            self.detach()

    @property
    def pid(self):
        return self._process.pid

    def __getstate__(self):
        return self._out_path, self._in_path, self._cipher_name, self._symmetric_key

    def __setstate__(self, state):
        self._out_path, self._in_path, self._cipher_name, self._symmetric_key = state
        parent_in_file = os.open(self._in_path, os.O_RDONLY | os.O_NONBLOCK)
        parent_out_file = os.open(self._out_path, os.O_WRONLY)
        fcntl.fcntl(parent_in_file, fcntl.F_SETFL, os.O_RDONLY)
        send, recv = make_send(parent_out_file), make_recv(parent_in_file)
        self._send, self._recv = secure_channel(send, recv, self._cipher_name, self._symmetric_key)

    def wait(self, timeout=None):
        return self._process.wait(timeout)

    def __enter__(self):
        self._process.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.detach()
        return self._process.__exit__(exc_type, exc_val, exc_tb)

    def request(self, endpoint, *args, **kwargs):
        request = Request(endpoint, args, kwargs)
        try:
            self._send(pickle.dumps(request))
        except AttributeError:
            raise RuntimeError('Connection is lost') from None
        response = pickle.loads(self._recv())
        if response.error is not None:
            raise response.error
        return response.result

    def detach(self):
        for fd in self._fds:
            try:
                os.close(fd)
            except OSError:
                pass
        try:
            del self._send, self._recv
        except AttributeError:
            pass
        try:
            os.remove(self._out_path)
            os.remove(self._in_path)
        except (OSError, FileNotFoundError, AttributeError):
            pass


def _make_fifo(path: str | None = None):
    """Open FIFO at specified path or create and open a new one."""
    if path is None:
        path = os.path.join('/tmp', secrets.token_urlsafe(16))
        os.mkfifo(path)
    in_fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    out_fd = os.open(path, os.O_WRONLY)
    fcntl.fcntl(in_fd, fcntl.F_SETFL, os.O_RDONLY)
    return in_fd, out_fd, path


_loader_code_template = """
g = globals().copy()
import os, sys
from creepy.subprocess import App, common
sys.argv, App._stdin, App._stdout = {args!r}, {fdr}, {fdw}
filename = sys.argv[0]
recv = common.make_recv(App._stdin)
code_object = compile(recv(), filename, 'exec')
try:
    g.update({{'__name__': '__main__', '__file__': filename}})
    exec(code_object, g)
except Exception:
    import traceback
    traceback.print_exc()
finally:
    try:
        os.write({fdw}, b'\\0')
    except BrokenPipeError:
        pass
""".strip()
