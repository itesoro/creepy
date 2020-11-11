from dataclasses import dataclass, field


class Scope:
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

    def encode(self, message: str) -> str:
        return self._cipher.encode(message)

    def decode(self, ciphertext: str) -> str:
        return self._cipher.decode(ciphertext)


@dataclass
class Session:
    cipher: object
    scope: Scope = field(default_factory=Scope)
