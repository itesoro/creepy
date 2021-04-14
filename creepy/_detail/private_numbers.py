import getpass

from cryptography.hazmat import backends
from cryptography.hazmat.primitives import serialization

import creepy.pipe
from creepy.memory import mlockall


assert __name__ == '__main__', f"File {repr(__file__)} shouldn't be used as a module"

try:
    mlockall()
except RuntimeError as e:
    print(e)

app = creepy.pipe.App()


def _load_private_key(path, passphrase):
    key_bytes = open(path, 'rb').read()
    loaders = [serialization.load_pem_private_key, serialization.load_ssh_private_key]
    backend = backends.default_backend()
    for i in range(4):
        if i > 0:
            passphrase = getpass.getpass(prompt=f"Enter passphrase for private_key {repr(path)}: ").encode()
        for loader in loaders:
            try:
                return loader(key_bytes, passphrase, backend=backend)
            except (TypeError, ValueError):
                pass
    return None


@app.route('get')
def get(path, passphrase):
    """
    Returns private numbers
    """
    private_key = _load_private_key(path, passphrase)
    private_numbers = private_key.private_numbers()
    del private_key
    return private_numbers


app.run()
