import typing
from functools import partial
from inspect import Signature, Parameter


if typing.TYPE_CHECKING:
    from .pypen import Pypen


def instantiate(process: "Pypen"):
    """Creates an instance representing the given process's routes as methods of this instance."""
    interface = process.request('_interface')
    return _ProxyObject(process, interface)


class _default_value:
    """
    Represents a placeholder for default values in method arguments of a proxy object.

    This class acts as a sentinel indicating the presence of a default value for an argument, without specifying the
    actual value. It is used primarily in the construction of method signatures for the proxy object.
    """


class _ProxyObject:
    def __init__(self, process: "Pypen", interface: dict):
        self._process = process
        self._signatures, self._docs = {}, {}
        for func_name, func in interface.items():
            params = []
            for name, kind, has_default in func['params']:
                param = Parameter(name, kind, default=_default_value() if has_default else Parameter.empty)
                params.append(param)
            self._signatures[func_name] = Signature(params)
            self._docs[func_name] = func['doc']

    def __getattr__(self, name):
        func = partial(self._proxy_func, name)
        func.__doc__ = self._docs[name]
        return func

    def _proxy_func(self, func_name: str, *args, **kwargs):
        self._signatures[func_name].bind(*args, **kwargs)  # Raise on client if parameters don't match the signature
        return self._process.request(func_name, *args, **kwargs)
