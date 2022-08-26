import os
import re
import logging
import requests
import warnings
import importlib
from typing import Tuple
from contextlib import contextmanager

from ..serialization import load_private_key
from ..protocol import make_cipher, HandshakeProtocol
from ..protocol.constants import NONCE_SIZE
from . import pickle
from .proxy import ProxyObject, VersionQuery, DownloadQuery, DelQuery, proxy_flags


logger = logging.getLogger('creepy')


def unproxy(*objs):
    """
    Get the object behind a proxy or object itself if it isn't instance of ProxyObject.
    """
    res = list(objs)
    remotes = {}
    for i, obj in enumerate(objs):
        if isinstance(obj, ProxyObject):
            v = remotes.get(obj._remote)
            if v is None:
                v = remotes[obj._remote] = [], []
            indices, proxied_objs = v
            indices.append(i)
            proxied_objs.append(obj)
    for remote, (indices, proxied_objs) in remotes.items():
        unproxied = remote._get(*proxied_objs)
        if len(indices) == 1:
            res[indices[0]] = unproxied
        else:
            for src_i, dst_i in enumerate(indices):
                res[dst_i] = unproxied[src_i]
    return res[0] if len(res) == 1 else res


def _make_request(url, data=None, **kwargs):
    response = requests.post(url, data, **kwargs)
    if response.status_code == 200:
        return response.content
    raise RuntimeError(f'{url}: {response.content}')


class _Local:
    def __init__(self):
        self.os = os

    def __repr__(self):
        return 'self'

    def path(self, path: str):
        return (self, path)

    def import_module(self, name):
        return importlib.import_module(name)

    @property
    def open(self):
        return open


class Remote:
    def __init__(self, url, session_id, cipher):
        self._url = url
        self._session_id = session_id
        self._cipher = cipher
        self._nonce = 0
        self._imports = {}
        self._del_queue = []
        try:
            self._version = self._post(VersionQuery())
        except Exception:
            self._version = 0

    def disconnect(self):
        if self._url is None:
            return
        self._del_queue.append(0)
        try:
            self._post()
        finally:
            self._url = None
            self._session_id = None
            self._cipher = None
            self._nonce = None
            self._imports = None

    def path(self, path: str):
        return (self, path)

    def __repr__(self):
        return self._url

    # TODO(Roman Rizvanov): Impelement [named] scopes instead of misleading globals() function.
    @property
    def globals(self):
        assert os.__class__ == re.__class__
        flags = proxy_flags(os.__class__)  # it's ok to use any module instead of `os`
        return ProxyObject(self, 0, flags, 'module')

    def import_module(self, name):
        module = self._imports.get(name, None)
        if module is None:
            self._imports[name] = module = self.globals.__import__(name)
        return module

    @property
    def open(self):
        return self.globals.open

    @property
    def os(self):
        return self.import_module('os')

    def _make_del_query(self):
        res = None
        if len(self._del_queue) > 0:
            res = DelQuery(self._del_queue)
            self._del_queue = []
        return res

    def _post(self, *query):
        query = list(query)
        if len(self._del_queue) > 0:
            query.append(DelQuery(self._del_queue))
            self._del_queue = []
        data = self._nonce.to_bytes(NONCE_SIZE, 'big') + pickle.dumps(*query)
        self._nonce += 1
        response = _make_request(self._url, self._session_id + self._cipher.encrypt(data))
        res = pickle.loads(self._cipher.decrypt(response))
        if isinstance(res, Exception):
            raise res
        return res

    def _lazy_delete(self, id):
        self._del_queue.append(id)

    def _get(self, *objs: Tuple[ProxyObject]):
        ids = []
        for obj in objs:
            assert obj._remote == self
            ids.append(obj._id)
        if self._version == 0:
            res = []
            for id in ids:
                res.append(self._post(DownloadQuery(id=id)))
        else:
            res = self._post(DownloadQuery(ids=ids))
        return res[0] if len(res) == 1 else res

    def download(self, obj: ProxyObject):
        warnings.warn('Deprecated, use ProxyObject._get() instead', category=DeprecationWarning)
        return self._get(obj)


@contextmanager
def connect(url, private_key=None):
    if url == 'self':
        try:
            yield _self_node
        finally:
            return
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
    try:
        remote = Remote(url, session_id, cipher)
        # TODO(Roman Rizvanov): Make Remote class to be contextmanager.
        yield remote
    finally:
        remote.disconnect()


_self_node = _Local()
