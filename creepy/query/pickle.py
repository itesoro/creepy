import io
import pickle

from ..protocol.constants import PICKLE_PROTOCOL
from .proxy import ProxyObject


class _Pickler(pickle.Pickler):
    def persistent_id(self, obj):
        try:
            if id(ProxyObject.__slots__) == id(obj.__slots__):
                return obj._id
        except Exception:
            pass


class _Unpickler(pickle.Unpickler):
    def __init__(self, scope, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scope = scope

    def persistent_load(self, pid):
        return self.scope.get(pid)


def load(f, scope=None):
    return _Unpickler(scope, f).load()


def dumps(*objs):
    f = io.BytesIO()
    for obj in objs:
        _Pickler(f, PICKLE_PROTOCOL).dump(obj)
    return f.getvalue()


def loads(data, scope=None):
    f = io.BytesIO(data)
    return load(f, scope)
