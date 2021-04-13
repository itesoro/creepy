import os
from typing import Optional

from .pipe import connect
from .protocol.common import id_filenames


class ProcessifiedPrivateKey:
    def __init__(self, session):
        from cryptography.hazmat.primitives import serialization
        self._session = session
        public_bytes = session.request('public_bytes')
        self._public_key = serialization.load_ssh_public_key(public_bytes)

    def public_key(self):
        return self._public_key

    def decrypt(self, ciphertext: bytes, padding=None) -> bytes:
        return self._session.request('decrypt', ciphertext, padding)

    def sign(self, message: bytes, padding = None, algorithm = None) -> bytes:
        return self._session.request('sign', message, padding, algorithm)


def load_private_key(path: Optional[str] = None, passphrase: Optional[str] = None):
    # TODO(Roman Rizvanov): Make `passphrase` to be `SecureString`.
    session = connect('_detail/private_key')
    if path is None:
        ssh_dir = os.path.expanduser('~/.ssh')
        for id_filename in id_filenames:
            path = os.path.join(ssh_dir, id_filename)
            if os.path.isfile(path):
                break
    else:
        path = os.path.expanduser(path)
    session.request('load', path, passphrase)
    return ProcessifiedPrivateKey(session)
