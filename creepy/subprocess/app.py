import pickle

from .common import Request, Response, make_send, make_recv, secure_bob


class App:
    _stdin = 0
    _stdout = 1

    def __init__(self) -> None:
        self._routes = {}

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
