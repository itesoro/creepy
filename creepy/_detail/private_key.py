from typing import Optional

from cryptography.hazmat import backends
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding as crypto_padding

from creepy.subprocess import App, Pypen


assert __name__ == '__main__', f"File {__file__!r} shouldn't be used as a module"


_private_key = None
app = App()


class _Loader:
    def __init__(self, path: str, passphrase=None):
        self.path = path
        self.passphrase = passphrase

    def __call__(self):
        with Pypen('private_numbers',
                   hash='73051c13d71e1404adabdf9a341b6e7f9e31361361017961ac92c60cb2661cd1') as session:
            private_numbers = session.request('get', self.path, self.passphrase)
        global _private_key
        _private_key = backends.default_backend().load_rsa_private_numbers(private_numbers,
                                                                           unsafe_skip_rsa_key_validation=False)


def _get_private_key():
    if _private_key is None:
        global _loader
        _loader()
        del _loader
    return _private_key


@app.route('load')
def lazy_load(path: str, passphrase=None):
    global _loader
    _loader = _Loader(path, passphrase)


@app.route('enter_passphrase')
def enter_passphrase(passphrase):
    _loader.passphrase = passphrase


@app.route('public_bytes')
def public_bytes(encoding=serialization.Encoding.OpenSSH, format=serialization.PublicFormat.OpenSSH):
    public_key = _get_private_key().public_key()
    return public_key.public_bytes(encoding, format)


@app.route('sign')
def sign(message: bytes,
         padding: Optional[crypto_padding.AsymmetricPadding] = None,
         algorithm: Optional[hashes.HashAlgorithm] = None) -> bytes:
    if padding is None:
        padding = crypto_padding.PSS(
            mgf=crypto_padding.MGF1(hashes.SHA256()),
            salt_length=crypto_padding.PSS.MAX_LENGTH
        )
    if algorithm is None:
        algorithm = hashes.SHA256()
    return _get_private_key().sign(message, padding, algorithm)


@app.route('decrypt')
def decrypt(ciphertext: bytes, padding=None) -> bytes:
    if padding is None:
        padding = crypto_padding.OAEP(
            mgf=crypto_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    return _get_private_key().decrypt(ciphertext, padding)


app.run()

# References:
# - Asymmetric algorithms https://cryptography.io/en/latest/hazmat/primitives/asymmetric/
# - RSA https://cryptography.io/en/latest/hazmat/primitives/asymmetric/rsa/
