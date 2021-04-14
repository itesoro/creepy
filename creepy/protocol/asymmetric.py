from typing import Optional

from cryptography.hazmat import backends
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature

from ..serialization import ProcessifiedPrivateKey


_ENCRYPT_PADDING = padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
_SIGN_PADDING = padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH)
_SIGN_ALGORITHM = hashes.SHA512()


def encrypt(public_key, plaintext: bytes) -> bytes:
    return public_key.encrypt(plaintext, _ENCRYPT_PADDING)


def decrypt(private_key, ciphertext: bytes) -> bytes:
    return private_key.decrypt(ciphertext, _ENCRYPT_PADDING)


def sign(private_key, plaintext: Optional[bytes] = None) -> bytes:
    if isinstance(private_key, ProcessifiedPrivateKey):
        # `padding=_SIGN_PADDING` isn't passed because at the moment of writting it isn't serialized correctly.
        return private_key.sign(plaintext, algorithm=_SIGN_ALGORITHM)
    return private_key.sign(plaintext, _SIGN_PADDING, _SIGN_ALGORITHM)


def verify(public_key, signature: bytes, plaintext: Optional[bytes] = None) -> None:
    public_key.verify(signature, plaintext, _SIGN_PADDING, _SIGN_ALGORITHM)


def fingerprint(public_key) -> str:
    key_bytes = public_key.public_bytes(encoding=serialization.Encoding.DER,
                                        format=serialization.PublicFormat.SubjectPublicKeyInfo)
    hasher = hashes.Hash(hashes.SHA256(), backends.default_backend())
    hasher.update(key_bytes)
    return hasher.finalize()[:16].hex()
