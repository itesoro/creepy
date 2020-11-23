from typing import List
from dataclasses import dataclass


@dataclass
class DownloadQuery:
    id: int

    def __call__(self, scope):
        return scope.get(self.id)


@dataclass
class DelQuery:
    ids: List[int]

    def __call__(self, scope):
        for id in self.ids:
            scope.pop(id)


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
            self._remote._lazy_delete(id)

    def __getstate__(self):
        return self._id

    def __setstate__(self, value):
        self._id = value

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
    __getitem__ = _catch_magic_call('__getitem__')
    __len__ = _catch_magic_call('__len__')
    __iter__ = _catch_magic_call('__iter__')
    __next__ = _catch_magic_call('__next__')
    __bool__ = _catch_magic_call_nd_download('__bool__')
    __str__ = _catch_magic_call_nd_download('__str__')
    __repr__ = _catch_magic_call_nd_download('__repr__')
