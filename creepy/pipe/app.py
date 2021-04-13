import sys
import struct
import pickle
import contextlib

from .common import Request, Response, make_send, make_recv, secure_bob


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
                try:
                    request = pickle.loads(recv())
                except struct.error:
                    break
                assert type(request) is Request
                handler = self._routes.get(request.rule)
                response = Response()
                try:
                    response.result = handler(*request.args, **request.kwargs)
                except Exception as e:
                    response.error = e
                send(pickle.dumps(response))
