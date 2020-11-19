import os
import re
import shutil
import pickle
import logging
import tempfile
import requests
from dataclasses import dataclass

from creepy.protocol import load_private_key, make_cipher, HandshakeProtocol
from creepy.protocol.constants import PICKLE_PROTOCOL, NONCE_SIZE


logger = logging.getLogger('creepy')


@dataclass
class DownloadQuery:
    id: int

    def __call__(self, scope):
        return scope.get(self.id)


@dataclass
class DelQuery:
    id: int

    def __call__(self, scope):
        scope.pop(self.id)


@dataclass
class GetattrQuery:
    id: int
    name: str

    def __call__(self, scope):
        x = scope.get(self.id)
        y = getattr(x, self.name)
        return scope.put(y)


@dataclass
class SetattrQuery:
    id: int
    name: str
    value: object

    def __call__(self, scope):
        x = scope.get(self.id)
        setattr(x, self.name, self.value)


@dataclass
class DelattrQuery:
    id: int
    name: str

    def __call__(self, scope):
        x = scope.get(self.id)
        delattr(x, self.name)


@dataclass
class CallQuery:
    id: int
    args: list
    kwargs: dict

    def __call__(self, scope):
        f = scope.get(self.id)
        r = f(*self.args, **self.kwargs)
        return scope.put(r)


class ProxyObject:
    def __init__(self, remote, id):
        object.__setattr__(self, '_remote', remote)
        object.__setattr__(self, '_id', id)

    def _make_child(self, query):
        remote = self._remote
        child_id = remote._post(query)
        return ProxyObject(remote, child_id)

    def __del__(self):
        id = self._id
        if id > 0:
            self._remote._post(DelQuery(id))

    def __getattr__(self, name):
        return self._make_child(GetattrQuery(self._id, name))

    def __setattr__(self, name, value):
        self._remote._post(SetattrQuery(self._id, name, value))

    def __delattr__(self, name):
        self._remote._post(DelattrQuery(self._id, name))

    def __call__(self, *args, **kwargs):
        return self._make_child(CallQuery(self._id, args, kwargs))

    def _catch_magic_call(name):
        def handler(self, *args, **kwargs):
            return self.__getattr__(name)(*args, **kwargs)
        return handler

    def _catch_magic_call_nd_download(name):
        def handler(self, *args, **kwargs):
            return self._remote.download(self.__getattr__(name)(*args, **kwargs))
        return handler

    __enter__ = _catch_magic_call('__enter__')
    __exit__ = _catch_magic_call('__exit__')
    __bool__ = _catch_magic_call_nd_download('__bool__')
    __str__ = _catch_magic_call_nd_download('__str__')
    __repr__ = _catch_magic_call_nd_download('__repr__')


def _make_request(url, data=None, **kwargs):
    response = requests.post(url, data, **kwargs)
    if response.status_code == 200:
        return response.content
    logger.error(f'{url}: {response.content}')
    return None


class Remote:
    def __init__(self, url, session_id, cipher):
        self._url = url
        self._session_id = session_id
        self._cipher = cipher
        self._nonce = 0
        self._imports = {}

    @property
    def globals(self):
        return ProxyObject(self, 0)

    def import_module(self, name):
        module = self._imports.get(name, None)
        if module is None:
            self._imports[name] = module = self.globals.__builtins__.__import__(name)
        return module

    def _post(self, query):
        data = self._nonce.to_bytes(NONCE_SIZE, 'big') + pickle.dumps(query, PICKLE_PROTOCOL)
        self._nonce += 1
        response = _make_request(self._url, self._session_id + self._cipher.encrypt(data))
        if response is None:
            raise ValueError()
        res = pickle.loads(self._cipher.decrypt(response))
        if isinstance(res, Exception):
            raise res
        return res

    def download(self, obj: ProxyObject):
        assert self == obj._remote, 'The object is on a different node'
        return self._post(DownloadQuery(obj._id))

    def _send_file(self, src_path: str, dst_path: str, exist_ok=False):
        CHUNK_SIZE = 2**24
        if not exist_ok and self.globals.os.path.exists(dst_path):
            raise OSError(f"Path exists: '{dst_path}'")
        with self.globals.open(dst_path, 'wb') as dst_f:
            with open(src_path, 'rb') as src_f:
                while True:
                    chunk = src_f.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    n = CHUNK_SIZE
                    for i in reversed(range(4)):
                        try:
                            while True:
                                dst_f.write(chunk[:n])
                                if len(chunk) <= n:
                                    break
                                chunk = chunk[n:]
                            break
                        except Exception as e:
                            logger.exception(e)
                            if i == 0:
                                raise
                            n /= 2

    def _send_directory(self, src_dir: str, dst_dir: str, exist_ok=False):
        remote_os = self.globals.os
        remote_os.makedirs(dst_dir, exist_ok=exist_ok)
        for src_root, dirs, files in os.walk(src_dir):
            dst_root = os.path.join(dst_dir, os.path.relpath(src_root, src_dir))
            for name in files:
                self._send_file(os.path.join(src_root, name), os.path.join(dst_root, name))
            for name in dirs:
                remote_os.makedirs(os.path.join(dst_root, name), exist_ok=exist_ok)

    def send(self, src_path: str, dst_path: str, exist_ok=False, archive=True):
        src_path = os.path.abspath(os.path.expanduser(src_path))
        if archive and os.path.isdir(src_path):
            r_tempfile = self.import_module('tempfile')
            r_shutil = self.import_module('shutil')
            ARCHIVE_FORMAT = 'gztar'
            if not exist_ok and self.globals.os.path.exists(dst_path):
                raise OSError(f"Path exists: '{dst_path}'")
            with tempfile.TemporaryDirectory() as tmp_dir:
                with r_tempfile.TemporaryDirectory() as remote_tmp_dir:
                    archive_path = shutil.make_archive(
                        os.path.join(tmp_dir, 'temp'),
                        ARCHIVE_FORMAT,
                        src_path
                    )
                    r_archive_path = os.path.join(
                        self.download(remote_tmp_dir),
                        os.path.basename(archive_path)
                    )
                    self._send_file(archive_path, r_archive_path, exist_ok=False)
                    r_shutil.unpack_archive(r_archive_path, dst_path, format=ARCHIVE_FORMAT)
            return
        if os.path.isfile(src_path):
            return self._send_file(src_path, dst_path, exist_ok)
        return self._send_directory(src_path, dst_path, exist_ok)


def connect(url, private_key=None):
    if not re.search(r'^(\w+)://', url):
        url = 'http://' + url
    if private_key is None:
        private_key = load_private_key()
        if private_key is None:
            return None

    def public_channel(endpoint, data=None):
        return _make_request(f'{url}{endpoint}', data, timeout=10)

    session_id, cipher_name, cipher_key = HandshakeProtocol.hi_alice(private_key, public_channel)
    cipher = make_cipher(cipher_name, cipher_key)
    return Remote(url, session_id, cipher)
