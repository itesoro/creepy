from typing import Optional

from cryptography.hazmat import backends
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding as crypto_padding
from cryptography.hazmat.primitives.asymmetric import rsa

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
                   hash='7723c366d84dd7cd818dfbbfacdf3bee0ad44aeb11d54f4e8c68bffbe9da3809') as session:
            session.request('load', self.path, self.passphrase)
            n, e = session.request('get_public_numbers')
            d = session.request('get_d')
        global _private_key
        _private_key = _deserialize_private_key(n, e, d)


def _get_private_key():
    if _private_key is None:
        global _loader
        _loader()
        del _loader
    return _private_key


def _deserialize_private_key(n, e, d):
    p, q = rsa.rsa_recover_prime_factors(n, e, d)
    iqmp = rsa.rsa_crt_iqmp(p, q)
    dmp1 = rsa.rsa_crt_dmp1(d, p)
    dmq1 = rsa.rsa_crt_dmq1(d, q)
    private_numbers = rsa.RSAPrivateNumbers(p, q, d, dmp1, dmq1, iqmp, rsa.RSAPublicNumbers(e, n))
    return private_numbers.private_key(backend=backends.default_backend())


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
