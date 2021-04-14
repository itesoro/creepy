import os
from typing import Optional


class ProcessifiedPrivateKey:
    def __init__(self, session):
        self._session = session
        self._public_key = None

    def public_key(self):
        if self._public_key is None:
            from cryptography.hazmat.primitives import serialization
            public_bytes = self._session.request('public_bytes')
            self._public_key = serialization.load_ssh_public_key(public_bytes)
        return self._public_key

    def decrypt(self, ciphertext: bytes, padding=None) -> bytes:
        return self._session.request('decrypt', ciphertext, padding)

    def sign(self, message: bytes, padding = None, algorithm = None) -> bytes:
        return self._session.request('sign', message, padding, algorithm)


_id_filenames = ['id_rsa', 'id_dsa', 'id_ecdsa', 'id_ed25519']


def _find_key(path: Optional[str], ext: str = '', ssh_dir: Optional[str] = None) -> str:
    if path is not None:
        return os.path.expanduser(path)
    if ssh_dir is None:
        ssh_dir = os.path.expanduser('~/.ssh')
    for id_filename in _id_filenames:
        path = os.path.join(ssh_dir, id_filename + ext)
        if os.path.isfile(path):
            return path


def load_private_key(path: Optional[str] = None, passphrase: Optional[str] = None, ssh_dir: Optional[str] = None):
    from .pipe import connect
    # TODO(Roman Rizvanov): Make `passphrase` to be `SecureString`.
    path = _find_key(path, ssh_dir=ssh_dir)
    if path is None:
        raise RuntimeError('Failed to find private key file')
    session = connect('_detail/private_key', 'cdae7ab74846eb142beba39333f02b5ab3193025019ce111d76eab79c9889c70')
    session.request('load', path, passphrase)
    return ProcessifiedPrivateKey(session)


def parse_public_key(key_bytes: bytes):
    from cryptography.hazmat import backends
    from cryptography.hazmat.primitives import serialization
    loaders = [serialization.load_pem_public_key, serialization.load_ssh_public_key]
    backend = backends.default_backend()
    for loader in loaders:
        try:
            return loader(key_bytes, backend=backend)
        except (TypeError, ValueError):
            pass
    return ValueError('Invalid key format')


def load_public_key(path: Optional[str] = None, ssh_dir: Optional[str] = None):
    path = _find_key(path, '.pub', ssh_dir=ssh_dir)
    if path is None:
        raise RuntimeError('Failed to find public key file')
    key_bytes = open(path, 'rb').read()
    return parse_public_key(key_bytes)
