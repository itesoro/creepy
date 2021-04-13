from typing import Optional

from cryptography.hazmat import backends
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding as crypto_padding

import creepy.pipe


assert __name__ == '__main__', f"File {repr(__file__)} shouldn't be used as a module"


app = creepy.pipe.App()


@app.route('load')
def load(path: str, passphrase: Optional[str] = None):
    with creepy.pipe.connect('private_numbers') as session:
        private_numbers = session.request('get', path, passphrase)
    global _private_key, _public_key
    _private_key = backends.default_backend().load_rsa_private_numbers(private_numbers)
    _public_key = _private_key.public_key()


@app.route('public_bytes')
def public_bytes(encoding=serialization.Encoding.OpenSSH, format=serialization.PublicFormat.OpenSSH):
    return _public_key.public_bytes(encoding, format)


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
    return _private_key.sign(message, padding, algorithm)


@app.route('decrypt')
def decrypt(ciphertext: bytes, padding=None) -> bytes:
    if padding is None:
        padding = crypto_padding.OAEP(
            mgf=crypto_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    return _private_key.decrypt(ciphertext, padding)


app.run()

# References:
# - Asymmetric algorithms https://cryptography.io/en/latest/hazmat/primitives/asymmetric/
# - RSA https://cryptography.io/en/latest/hazmat/primitives/asymmetric/rsa/
