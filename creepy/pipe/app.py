import sys
import pickle
import contextlib

from .common import Request, make_send, make_recv, secure_bob


class App:
    def __init__(self) -> None:
        self._routes = {}

    def route(self, rule: str):
        def decorator(fn):
            self._routes[rule] = fn
            return fn
        return decorator

    def run(self):
        send = make_send(sys.stdout.buffer)
        recv = make_recv(sys.stdin.buffer)
        with contextlib.redirect_stdout(sys.stderr):
            send, recv = secure_bob(send, recv)
            while True:
                request = pickle.loads(recv())
                assert type(request) is Request
                handler = self._routes.get(request.rule)
                result = handler(*request.args, **request.kwargs)
                send(pickle.dumps(result))
