import getpass
from typing import Optional

from cryptography.hazmat import backends
from cryptography.hazmat.primitives import serialization

import creepy.pipe
from creepy.types import SecureString
from creepy.utils.libc import mlockall, MCL_FUTURE


assert __name__ == '__main__', f"File {repr(__file__)} shouldn't be used as a module"
app = creepy.pipe.App()


def _load_private_key(path, passphrase: Optional[SecureString]):
    key_bytes = open(path, 'rb').read()
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


@app.route('get')
def get(path, passphrase):
    """
    Returns private numbers
    """
    private_key = _load_private_key(path, passphrase)
    private_numbers = private_key.private_numbers()
    del private_key
    return private_numbers


mlockall(MCL_FUTURE)
app.run()
