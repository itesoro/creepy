import os
import pickle
import requests
import base64
from dataclasses import dataclass


PICKLE_PROTOCOL = 4


class Context:
    def __init__(self):
        self._vars = {}
        self._available = []
        self._n = -1

    def put(self, value):
        try:
            i = self._available.pop()
        except Exception:
            self._n += 1
            i = self._n
        self._vars[i] = value
        return i

    def get(self, id):
        value = self._vars.get(id)
        return value

    def pop(self, id):
        value = self._vars.pop(id)
        if id < self._n:
            self._available.append(id)
        else:
            assert id == self._n
            self._n -= 1
        return value


@dataclass
class DownloadQuery:
    id: int

    def __call__(self, context):
        return context.get(self.id)


@dataclass
class DelQuery:
    id: int

    def __call__(self, context):
        context.pop(self.id)


@dataclass
class GetattrQuery:
    id: int
    name: str

    def __call__(self, context):
        x = context.get(self.id)
        y = getattr(x, self.name)
        return context.put(y)


@dataclass
class SetattrQuery:
    id: int
    name: str
    value: object

    def __call__(self, context):
        x = context.get(self.id)
        setattr(x, self.name, self.value)


@dataclass
class DelattrQuery:
    id: int
    name: str

    def __call__(self, context):
        x = context.get(self.id)
        delattr(x, self.name, value)


@dataclass
class CallQuery:
    id: int
    args: list
    kwargs: dict

    def __call__(self, context):
        f = context.get(self.id)
        r = f(*self.args, **self.kwargs)
        return context.put(r)


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


class Remote:
    PICKLE_PROTOCOL = 4

    def __init__(self, url, private_key=None):
        self._url = url
        self._private_key = private_key

    @property
    def scope(self):
        return ProxyObject(self, 0)

    def _post(self, query):
        headers = {'content-type': 'application/octet-stream'}
        data = pickle.dumps(query, PICKLE_PROTOCOL)
        response = requests.post(self._url, data)
        res = pickle.loads(response.content)
        if isinstance(res, Exception):
            raise res
        return res

    def download(self, obj: ProxyObject):
        assert self == obj._remote, 'The object is on a different node'
        return self._post(DownloadQuery(obj._id))

    def send_file(self, src_path: str, dst_path: str, exist_ok=False):
        CHUNK_SIZE = 2**18
        if not exist_ok and self.scope.os.path.exists(dst_path):
            raise OSError("File exists: '{dst_path}'")
        with self.scope.open(dst_path, 'wb') as dst_f:
            with open(src_path, 'rb') as src_f:
                while True:
                    chunk = src_f.read(CHUNK_SIZE)  
                    if not chunk:
                        break
                    dst_f.write(chunk))

    def send_directory(self, src_dir: str, dst_dir: str, exist_ok=False):
        remote_os = self.scope.os
        remote_os.makedirs(dst_root, exist_ok=exist_ok)
        for src_root, dirs, files in os.walk(src_dir):
            dst_root = os.path.join(dst_dir, os.relpath(src_root, src_dir))
            for name in files:
                self.send_file(os.path.join(src_root, name), os.path.join(dst_root, name))
            for name in dirs:
                remote_os.makedirs(os.path.join(dst_root, name), exist_ok=exist_ok)
