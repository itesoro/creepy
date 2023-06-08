import secrets
from cryptography.hazmat.primitives.ciphers import aead


class ChaCha20Poly1305:
    KEY_BITS = 256
    NONCE_BYTES = 12

    @property
    def name(self):
        return type(self).__name__

    def __init__(self, key):
        assert len(key) * 8 == self.KEY_BITS
        self._cipher = aead.ChaCha20Poly1305(key)
        self.key = key

    def encrypt(self, message):
        nonce = secrets.token_bytes(self.NONCE_BYTES)
        ciphertext = nonce + self._cipher.encrypt(nonce, message, b'')
        return ciphertext

    def decrypt(self, ciphertext):
        return self._cipher.decrypt(ciphertext[:self.NONCE_BYTES], ciphertext[self.NONCE_BYTES:], b'')


def make_cipher(algo_name, key=None):
    _symmetric_algos = {
        'ChaCha20Poly1305': ChaCha20Poly1305,
    }
    algo = _symmetric_algos.get(algo_name)
    if algo is None:
        raise AttributeError(algo_name)
    if key is None:
        key = secrets.token_bytes(algo.KEY_BITS // 8)
    return algo(key)
