import functools

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
        return _with_flags(y, scope.put(y))


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
        return _with_flags(r, scope.put(r))


def _catch_magic_call(name):
    def handler(self, *args, **kwargs):
        return self.__getattr__(name)(*args, **kwargs)
    return handler


def _catch_magic_call_nd_download(name):
    def handler(self, *args, **kwargs):
        return self._remote.download(self.__getattr__(name)(*args, **kwargs))
    return handler


def _make_child(self, query):
    remote = self._remote
    result = remote._post(query)
    if result.__class__ == int:
        # Old version
        child_id = result
        return ProxyObject(remote, child_id)
    return ProxyObject(remote, *result)


def _proxy__call__(self, *args, **kwargs):
    return _make_child(self, CallQuery(self._id, args, kwargs))


def _replace_with_result(fn):
    return fn()


def _memorize(f):
    cache = {}

    @functools.wraps(f)
    def wrapper(*args):
        result = cache.get(args)
        if result is None:
            cache[args] = result = f(*args)
        return result

    return wrapper


@_memorize
def _make_proxy_class_namespace(flags):
    namespace = {}
    for name, fn in _magics.items():
        if flags & 1:
            namespace[name] = fn[0]
        flags >>= 1
    return namespace


@_memorize
def _make_proxy_class(flags, class_name):
    base_proxy_cls = ProxyObject
    namespace = _make_proxy_class_namespace(flags)
    if class_name is not None:
        proxy_class_name = f'{base_proxy_cls.__name__}[{class_name}]'
    else:
        proxy_class_name = base_proxy_cls.__name__
    return type(proxy_class_name, (base_proxy_cls,), namespace)


@_memorize
def proxy_flags(cls):
    flags = 0
    for name in dir(cls):
        v = _magics.get(name)
        if v is not None:
            flags |= v[1]
    return flags


def _with_flags(value, id):
    cls = value.__class__
    return id, proxy_flags(cls), cls.__name__


class ProxyObject:
    __slots__ = ('_remote', '_id')

    def __new__(cls, remote, id, flags=-1, class_name=None):
        proxy_cls = _make_proxy_class(flags, class_name)
        ins = object.__new__(proxy_cls)
        object.__setattr__(ins, '_remote', remote)
        object.__setattr__(ins, '_id', id)
        return ins

    def __del__(self):
        id = self._id
        if id > 0:
            self._remote._lazy_delete(id)

    def __getattr__(self, name):
        return _make_child(self, GetattrQuery(self._id, name))

    def __setattr__(self, name, value):
        self._remote._post(SetattrQuery(self._id, name, value))

    def __delattr__(self, name):
        self._remote._post(DelattrQuery(self._id, name))


@_replace_with_result
def _magics():
    magics = [
        '__abs__', '__abstractmethods__', '__add__', '__aiter__', '__and__', '__anext__', '__await__', '__ceil__',
        '__contains__', '__delitem__', '__dir__', '__divmod__', '__enter__', '__eq__', '__exit__', '__floor__',
        '__floordiv__', '__format__', '__ge__', '__getformat__', '__getitem__', '__gt__', '__hash__', '__iadd__',
        '__iand__', '__imul__', '__index__', '__invert__', '__ior__', '__isub__', '__iter__', '__ixor__', '__le__',
        '__len__', '__lshift__', '__lt__', '__mod__', '__module__', '__mul__', '__ne__', '__neg__', '__next__',
        '__or__', '__pos__', '__pow__', '__radd__', '__rand__', '__rdivmod__', '__reversed__', '__rfloordiv__',
        '__rlshift__', '__rmod__', '__rmul__', '__ror__', '__round__', '__rpow__', '__rrshift__', '__rshift__',
        '__rsub__', '__rtruediv__', '__rxor__', '__setformat__', '__setitem__', '__sizeof__', '__sub__',
        '__subclasshook__', '__truediv__', '__trunc__', '__xor__'
    ]
    return_primitive_magics = [
        '__bool__', '__complex__', '__float__', '__instancecheck__', '__int__', '__repr__', '__str__',
        '__subclasscheck__'
    ]
    default_magics = {'__dir__', '__eq__', '__instancecheck__', '__ne__', '__repr__', '__str__', '__subclasscheck__'}
    namespace = {'__call__': _proxy__call__}

    def add_to_namespace(name, fn):
        if name in default_magics:
            setattr(ProxyObject, name, fn)
        else:
            namespace[name] = fn

    for name in magics:
        add_to_namespace(name, _catch_magic_call(name))
    for name in return_primitive_magics:
        add_to_namespace(name, _catch_magic_call_nd_download(name))
    bit = 1
    for name, fn in namespace.items():
        namespace[name] = (fn, bit)
        bit <<= 1
    return namespace
