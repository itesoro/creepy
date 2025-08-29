import os
import json
import base64
import struct
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from creepy.protocol.common import make_cipher


@dataclass
class Request:
    rule: str
    args: List[Any]
    kwargs: Dict[str, Any]


@dataclass
class Response:
    result: Optional[Any] = None
    error: Optional[Exception] = None


def make_recv(fd: int):
    def recv():
        size_header = os.read(fd, _SIZE_HEADER_STRUCT.size)
        size, = _SIZE_HEADER_STRUCT.unpack(size_header)
        return os.read(fd, size)
    return recv


def make_send(fd: int):
    def send(msg: bytes):
        os.write(fd, _SIZE_HEADER_STRUCT.pack(len(msg)))
        os.write(fd, msg)
    return send


def secure_channel(send, recv, cipher):
    def new_send(msg: bytes): send(cipher.encrypt(msg))
    def new_recv() -> bytes: return cipher.decrypt(recv())
    return new_send, new_recv


def secure_alice(send, recv, /, *, make_cipher=make_cipher):
    alice_private_key = ec.generate_private_key(ec.SECP384R1())
    alice_hello_msg = {
        'publicKey': _serialize_public_key(alice_private_key.public_key()),
    }
    send(json.dumps(alice_hello_msg).encode())
    bob_hello_msg = json.loads(recv().decode())
    bob_public_key = _deserialize_public_key(bob_hello_msg['publicKey'])
    cipher_name = bob_hello_msg['cipherName']
    derived_key = _derive_key(alice_private_key, bob_public_key)
    cipher = make_cipher(cipher_name, derived_key)
    return secure_channel(send, recv, cipher)


def secure_bob(send, recv, /, *, make_cipher=make_cipher):
    alice_hello_msg = json.loads(recv().decode())
    alice_public_key = _deserialize_public_key(alice_hello_msg['publicKey'])
    bob_private_key = ec.generate_private_key(ec.SECP384R1())
    cipher_name = 'ChaCha20Poly1305'
    bob_hello_msg = {
        'publicKey': _serialize_public_key(bob_private_key.public_key()),
        'cipherName': cipher_name,
    }
    send(json.dumps(bob_hello_msg).encode())
    derived_key = _derive_key(bob_private_key, alice_public_key)
    cipher = make_cipher(cipher_name, derived_key)
    return secure_channel(send, recv, cipher)


def _serialize_public_key(public_key: ec.EllipticCurvePublicKey) -> str:
    return base64.b64encode(
        public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
    ).decode('utf8')


def _deserialize_public_key(public_key: str) -> ec.EllipticCurvePublicKey:
    return serialization.load_der_public_key(base64.b64decode(public_key))


def _derive_key(private_key: ec.EllipticCurvePrivateKey, peer_public_key: ec.EllipticCurvePublicKey):
    shared_key = private_key.exchange(ec.ECDH(), peer_public_key)
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b'handshake data',
    ).derive(shared_key)


_SIZE_HEADER_STRUCT = struct.Struct('H')
