import sys
import getpass
import functools
from typing import Optional

from cryptography.hazmat import backends
from cryptography.hazmat.primitives import serialization

from creepy.subprocess import App
from creepy.types import SecureString
from creepy.utils.libc import mlockall, MCL_FUTURE


assert __name__ == '__main__', f"File {__file__!r} shouldn't be used as a module"
app = App()


def _load_private_key(path, passphrase: Optional[SecureString]):
    with open(path, 'rb') as f:
        key_bytes = f.read()
    loaders = [
        functools.partial(serialization.load_pem_private_key, unsafe_skip_rsa_key_validation=True),
        serialization.load_ssh_private_key
    ]
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
                return loader(key_bytes, passphrase)
            except (TypeError, ValueError):
                pass
    raise ValueError('Invalid passphrase')


@app.route('get')
def get(path, passphrase):
    """
    Returns private numbers
    """
    private_key = _load_private_key(path, passphrase)
    private_numbers = private_key.private_numbers()
    del private_key
    return private_numbers


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
