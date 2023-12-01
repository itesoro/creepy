import pickle
import inspect

from .common import Request, Response, make_send, make_recv, secure_bob


class App:
    _stdin = 0
    _stdout = 1

    def __init__(self) -> None:
        self._routes = {'_interface': self._interface}

    def route(self, rule: str):
        def decorator(fn):
            self._routes[rule] = fn
            return fn
        return decorator

    def run(self):
        send = make_send(self._stdout)
        recv = make_recv(self._stdin)
        send, recv = secure_bob(send, recv)
        while True:
            try:
                request = pickle.loads(recv())
            except BaseException:
                break
            assert type(request) is Request
            handler = self._routes.get(request.rule)
            response = Response()
            try:
                response.result = handler(*request.args, **request.kwargs)
            except Exception as e:
                response.error = e
            send(pickle.dumps(response))

    def _interface(self):
        interface = {}
        for func_name, func in self._routes.items():
            if func_name == '_interface':
                continue
            signature = inspect.signature(func)
            params = []
            for name, param in signature.parameters.items():
                has_default = not isinstance(param.default, inspect.Parameter.empty.__class__)
                params.append((name, param.kind.value, has_default))
            interface[func_name] = {"params": params, "doc": func.__doc__}
        return interface
