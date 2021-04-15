import secrets
import hashlib


def _f(x):
    return (x + 53) & 255


_nodes_pool = [[None, None] for _ in range(1024)]


def _new_node(value):
    i = secrets.randbelow(len(_nodes_pool))
    node = _nodes_pool[i]
    assert node[0] is None and node[1] is None
    _nodes_pool[i] = [None, None]
    node[1] = value
    return node


class SecureString:
    __slots__ = '_n', '_enter_count', '_tail', '_head', '_buffer'
    _hash_algo = hashlib.sha256

    def __init__(self):
        self.clear()

    def clear(self):
        self._n = 0
        self._tail = self._head = [None, 42]
        self._buffer = None
        self._enter_count = 0

    def _append_ord(self, x):
        self._tail[0] = _new_node(_f(self._tail[1]) ^ x)
        self._tail = self._tail[0]
        self._n += 1

    def append(self, c):
        assert len(c) == 1
        if isinstance(c, str):
            for x in c.encode():
                self._append_ord(x)
        else:
            self._append_ord(ord(c))

    def __getstate__(self) -> bytes:
        """
        Returns obfuscated bytes representation.
        """
        hasher = self._hash_algo()
        k = 1 + hasher.digest_size // 2
        m = k + self._n
        state = bytearray(1 + m + hasher.digest_size)
        state[0] = 0  # format version
        state[1:k] = secrets.token_bytes(k - 1)
        hasher.update(state[:k])
        x = self._head
        while x[0] is not None:
            for h in bytearray(hasher.digest()):
                y = x[0]
                if y is None:
                    break
                state[k] = h ^ _f(x[1]) ^ y[1]
                k += 1
                x = y
            hasher.update(state[k - hasher.digest_size : k])
        assert k == m
        return bytes(state[:m])

    def __setstate__(self, state: bytes):
        self.clear()
        state = bytearray(state)
        version = state[0]
        if version > 0:
            raise ValueError('`state` is invalid')
        hasher = self._hash_algo()
        k = 1 + hasher.digest_size // 2
        hasher.update(state[:k])
        while k < len(state):
            for h in bytearray(hasher.digest()):
                if k == len(state):
                    break
                self.append(chr(h ^ state[k]))
                k += 1
            hasher.update(state[k - hasher.digest_size : k])

    def __enter__(self) -> memoryview:
        self._enter_count += 1
        if self._enter_count == 1:
            assert self._buffer is None
            self._buffer = bytearray(self._n)
            x = self._head
            for i in range(self._n):
                y = x[0]
                self._buffer[i] = _f(x[1]) ^ y[1]
                x = y
            assert x[0] is None
        return memoryview(self._buffer)

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Fills string buffer returned by __enter__() with zeros.
        """
        self._enter_count -= 1
        if self._enter_count > 0:
            return
        assert self._enter_count == 0
        buffer, self._buffer = self._buffer, None
        for i in range(len(buffer)):
            buffer[i] = 0
