import os
import getpass
import secrets

from cryptography.hazmat import backends
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.ciphers import aead


id_filenames = ['id_rsa', 'id_dsa', 'id_ecdsa', 'id_ed25519']


class AES256GCM:
    KEY_BITS = 256
    NONCE_BYTES = 16

    @property
    def name(self):
        return type(self).__name__

    def __init__(self, key):
        assert len(key) * 8 == self.KEY_BITS
        self._cipher = aead.AESGCM(key)
        self.key = key

    def encrypt(self, message):
        nonce = secrets.token_bytes(self.NONCE_BYTES)
        ciphertext = nonce + self._cipher.encrypt(nonce, message, b'')
        return ciphertext

    def decrypt(self, ciphertext):
        return self._cipher.decrypt(ciphertext[:self.NONCE_BYTES], ciphertext[self.NONCE_BYTES:], b'')


def load_private_key(path=None, passphrase=None):
    if path is None:
        ssh_dir = os.path.expanduser('~/.ssh')
        for id_filename in id_filenames:
            path = os.path.join(ssh_dir, id_filename)
            if os.path.isfile(path):
                break
    else:
        path = os.path.expanduser(path)
    for _ in range(3):
        try:
            with open(path, 'rb') as f:
                key = serialization.load_pem_private_key(f.read(), passphrase, backend=backends.default_backend())
            return key
        except (TypeError, ValueError):
            pass
        try:
            with open(path, 'rb') as f:
                key = serialization.load_ssh_private_key(f.read(), passphrase, backend=backends.default_backend())
            return key
        except (TypeError, ValueError):
            passphrase = getpass.getpass(prompt=f"Enter passphrase for key '{path}': ").encode()
    return None


def make_cipher(algo_name, key=None):
    _symmetric_algos = {
        'AES256GCM': AES256GCM
    }
    algo = _symmetric_algos.get(algo_name)
    if algo is None:
        raise AttributeError(algo_name)
    if key is None:
        key = secrets.token_bytes(algo.KEY_BITS // 8)
    return algo(key)
