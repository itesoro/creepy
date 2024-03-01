import sys
import getpass
from typing import Optional

from cryptography.hazmat import backends
from cryptography.hazmat.primitives import serialization

from creepy.subprocess import App
from creepy.types import SecureString
from creepy.utils.libc import MCL_FUTURE, mlockall


assert __name__ == '__main__', f"File {__file__!r} shouldn't be used as a module"
app = App()
_private_key = None


def _load_private_key(path, passphrase: Optional[SecureString]):
    with open(path, 'rb') as f:
        key_bytes = f.read()
    loaders = [serialization.load_pem_private_key, serialization.load_ssh_private_key]
    backend = backends.default_backend()
    if passphrase is None:
        num_tries = 4
    else:
        assert type(passphrase) is SecureString
        passphrase = bytes(passphrase.__enter__())
        num_tries = 1
    for i in range(num_tries):
        if i > 0:
            passphrase = getpass.getpass(prompt=f"Enter passphrase for private_key {repr(path)}: ").encode()
        for loader in loaders:
            try:
                return loader(key_bytes, passphrase, backend=backend)
            except (TypeError, ValueError):
                pass
    raise ValueError('Invalid passphrase')


@app.route('load')
def load(path, passphrase: Optional[SecureString]):
    """Loads a private key from a file."""
    global _private_key
    if _private_key is not None:
        return
    _private_key = _load_private_key(path, passphrase)


@app.route('get_public_numbers')
def get_public_numbers():
    public_numbers = _private_key.public_key().public_numbers()
    return public_numbers.n, public_numbers.e


@app.route('get_d')
def get_d():
    private_numbers = _private_key.private_numbers()
    return private_numbers.d


try:
    mlockall(MCL_FUTURE)
except Exception:
    print(
        u'\033[1m\u001b[31m'  # enable bold & red
        u'[WARNING] Cannot lock memmory, `mlockall` is not available on your system.\n'
        u'          There is a chance that the passphrase you\'re about to enter will be dumped to the swap file.'
        u'\u001b[0m\033[0m',  # disable red & bold
        file=sys.stderr
    )

app.run()
