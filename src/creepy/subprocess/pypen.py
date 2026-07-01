import os
import sys
import json
import fcntl
import shlex
import pickle
import hashlib
import inspect
import secrets
import subprocess
from functools import cache
from inspect import Parameter, Signature
from typing import Optional

from ..protocol.common import make_cipher
from .common import Request, make_recv, make_send, secure_alice, secure_channel


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
            it should be specified without '.py' extension. Unless otherwise stated, it is recommended to pass `args`
            as a sequence.

            Inline code: If the first argument is the string '-c' then the second argument is treated as a Python
            source code string (similar to `python -c`). In this mode the code string is removed from `sys.argv` so
            that inside the executed code `sys.argv[0] == '-c'` and subsequent arguments follow (mirroring CPython
            behaviour). Example: `Pypen(['-c', 'print(1)'])`.
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
            first_arg = args[0]
        except IndexError:
            raise ValueError('`args` is invalid') from None

        if first_arg == '-c':  # Inline code execution mode
            if len(args) < 2:
                raise ValueError("'-c' requires a code string argument")
            code_string = args[1]
            # sys.argv should mimic python behaviour: ['-c', *remaining_args]
            args = ['-c'] + args[2:]
            filename = '-c'
            source_code = code_string.encode()
        else:  # File-based execution mode
            filename = first_arg
            try:
                caller_dir = os.path.dirname(inspect.stack(0)[1].filename)
                filename = os.path.join(caller_dir, filename)
            except Exception:
                pass
            filename = filename + '.py'
            with open(filename, 'rb') as f:
                source_code = f.read()
            args[0] = filename
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
            self._out_path = self._in_path = None
        self._serializable = serializable
        self._fds = (child_in_fd, parent_out_fd, parent_in_fd, child_out_fd)
        loader_code = _loader_code_template.format(
            args=args,
            fdr=child_in_fd,
            fdw=child_out_fd,
            out_path=self._out_path,
            in_path=self._in_path
        )
        args = [sys.executable, '-c', loader_code]
        kwargs['pass_fds'] = kwargs.get('pass_fds', ()) + (child_in_fd, child_out_fd)
        self._process = subprocess.Popen(args, **kwargs)
        send, recv = make_send(parent_out_fd), make_recv(parent_in_fd)
        send(source_code)
        try:
            self._send, self._recv = secure_alice(send, recv, make_cipher=self._save_and_make_cipher)
        except Exception:
            self.detach()

    @property
    def pid(self):
        return self._process.pid

    def compile(self):
        return _make_proxy_instance(self)

    def __getstate__(self):
        if not self._serializable:
            raise RuntimeError("Can't serialize non-serializable process")
        return self._out_path, self._in_path, self._cipher_name, self._symmetric_key

    def __setstate__(self, state):
        out_path, in_path, cipher_name, symmetric_key = state
        in_fd = os.open(in_path, os.O_RDONLY | os.O_NONBLOCK)
        out_fd = os.open(out_path, os.O_WRONLY)
        fcntl.fcntl(in_fd, fcntl.F_SETFL, os.O_RDONLY)
        send, recv = make_send(out_fd), make_recv(in_fd)
        cipher = self._save_and_make_cipher(cipher_name, symmetric_key)
        self._serializable = True
        self._fds = (in_fd, out_fd)
        self._send, self._recv = secure_channel(send, recv, cipher)
        self._out_path, self._in_path = out_path, in_path

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

    def _save_and_make_cipher(self, cipher_name, symmetric_key):
        self._cipher_name, self._symmetric_key = cipher_name, symmetric_key
        return make_cipher(cipher_name, symmetric_key)


def _make_proxy_instance(process):
    interface = process.request('_interface')
    return _make_proxy_type(interface)(process)


@cache
def _make_proxy_type(interface: str):
    attrs = {}
    for func_name, func in json.loads(interface).items():
        params = []
        for name, kind, has_default in func['params']:
            param = Parameter(name, kind, default=None if has_default else Parameter.empty)
            params.append(param)
        attrs[func_name] = _make_proxy_func(Signature(params), func_name)
        attrs[func_name].__doc__ = func['doc']

    def proxy_init(self, process):
        self._process = process

    def proxy_enter(self, *args, **kwargs):
        self._process.__enter__(*args, **kwargs)
        return self

    def proxy_exit(self, exc_type, exc_val, exc_tb):
        return self._process.__exit__(exc_type, exc_val, exc_tb)

    def proxy_reduce(self):
        return (_make_proxy_instance, (self._process,))

    attrs['__init__'] = proxy_init
    attrs['__enter__'] = proxy_enter
    attrs['__exit__'] = proxy_exit
    attrs['__reduce__'] = proxy_reduce
    return type('Proxy', (), attrs)


def _make_proxy_func(signature, func_name):
    return lambda self, *args, **kwargs: _proxy_func(self, signature, func_name, *args, **kwargs)


def _proxy_func(self, signature, func_name, *args, **kwargs):
    signature.bind(*args, **kwargs)  # Raise on client if parameters don't match the signature
    return self._process.request(func_name, *args, **kwargs)


def _make_fifo(path: str | None = None):
    """Open FIFO at specified path or create and open a new one."""
    if path is None:
        path = os.path.join('/tmp', secrets.token_urlsafe(16))
        os.mkfifo(path)
    # Open the FIFO for reading. `os.O_NONBLOCK` is used in order to prevent blocking the process when opening.
    in_fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    # Since we already opened the FIFO for reading, following open won't block.
    out_fd = os.open(path, os.O_WRONLY)
    # Set the file descriptor to just `O_RDONLY` in order to get rid of `O_NONBLOCK` and synchronize the execution of
    # the two processes.
    fcntl.fcntl(in_fd, fcntl.F_SETFL, os.O_RDONLY)
    return in_fd, out_fd, path


_loader_code_template = """
g = globals().copy()
import os, sys
from creepy.subprocess import App, common
sys.argv, App._stdin, App._stdout = {args!r}, {fdr}, {fdw}
first_arg = sys.argv[0]
recv = common.make_recv(App._stdin)
code_object = compile(recv(), first_arg, 'exec')
try:
    g['__name__'] = '__main__'
    if first_arg != '-c':
        g['__file__'] = first_arg
    exec(code_object, g)
except Exception:
    import traceback
    traceback.print_exc()
finally:
    try:
        os.write({fdw}, b'\\0')
    except BrokenPipeError:
        pass
    for path in ({out_path!r}, {in_path!r}):
        try:
            os.remove(path)
        except (OSError, TypeError):
            pass
""".strip()
