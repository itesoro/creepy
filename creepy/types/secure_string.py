import secrets
import hashlib
from array import array

import creepy.utils.libc as _libc


_nodes_pool = [[None, None] for _ in range(1024)]


def _xorshift32(x):
    x ^= (x << 13) & 0xffffffff
    x ^= x >> 17
    x ^= (x << 5) & 0xffffffff
    return x


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
        self._tail = self._head = [None, secrets.randbits(32)]
        self._buffer = None
        self._enter_count = 0

    def append_code(self, x: int):
        assert 0 <= x < 256
        self._tail[0] = _new_node(_xorshift32(self._tail[1]) ^ x)
        self._tail = self._tail[0]
        self._n += 1

    def append(self, c):
        assert len(c) == 1
        if isinstance(c, str):
            for x in c.encode():
                self.append_code(x)
        else:
            self.append_code(ord(c))

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, SecureString):
            return False
        x, y = self._head, o._head
        while True:
            z = _xorshift32(x[1] ^ y[1])
            x, y = x[0], y[0]
            if (x is None) or (y is None):
                return x == y
            if x[1] ^ y[1] != z:
                return False

    def __getstate__(self) -> bytes:
        """
        Return obfuscated bytes representation.
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
            for h in hasher.digest():
                y = x[0]
                if y is None:
                    break
                state[k] = h ^ _xorshift32(x[1]) ^ y[1]
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
            self._buffer = array('B', bytearray(self._n))
            _libc.mlock(*self._buffer.buffer_info())  # prevent buffer from swapping
            x = self._head
            for i in range(self._n):
                y = x[0]
                self._buffer[i] = _xorshift32(x[1]) ^ y[1]
                x = y
            assert x[0] is None
        return memoryview(self._buffer)

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Fill string buffer returned by __enter__() with zeros.
        """
        self._enter_count -= 1
        if self._enter_count > 0:
            return
        assert self._enter_count == 0
        buffer, self._buffer = self._buffer, None
        for i in range(len(buffer)):
            buffer[i] = 0
        _libc.munlock(*buffer.buffer_info())

    def hash(self):
        """
        Compute SHA256 hash.
        """
        hasher = self._hash_algo()
        x = self._head
        for _ in range(self._n):
            y = x[0]
            hasher.update(bytes([_xorshift32(x[1]) ^ y[1]]))
            x = y
        assert x[0] is None
        return hasher.digest()
