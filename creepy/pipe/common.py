import io
import struct
from dataclasses import dataclass
from typing import Any, List, Dict, Optional

from cryptography.hazmat import backends
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from creepy.protocol.common import make_cipher


_OAEP_PADDING = padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
_SIZE_HEADER_STRUCT = struct.Struct('H')


@dataclass
class Request:
    rule: str
    args: List[Any]
    kwargs: Dict[str, Any]


@dataclass
class Response:
    result: Optional[Any] = None
    error: Optional[Exception] = None


def make_recv(f: io.RawIOBase):
    def recv():
        size_header = f.read(_SIZE_HEADER_STRUCT.size)
        size, = _SIZE_HEADER_STRUCT.unpack(size_header)
        return f.read(size)
    return recv


def make_send(f: io.RawIOBase):
    def send(msg: bytes):
        f.write(_SIZE_HEADER_STRUCT.pack(len(msg)))
        f.write(msg)
        f.flush()
    return send


def _secure_channel(send, recv, cipher):
    def new_send(msg: bytes): send(cipher.encrypt(msg))
    def new_recv() -> bytes: return cipher.decrypt(recv())
    return new_send, new_recv


def secure_alice(send, recv):
    from cryptography.hazmat.primitives.asymmetric import rsa
    onetime_private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096,
    )
    onetime_public_key = onetime_private_key.public_key()
    send(onetime_public_key.public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH
    ))
    cipher_name = recv().decode()
    symmetric_key = onetime_private_key.decrypt(recv(), _OAEP_PADDING)
    cipher = make_cipher(cipher_name, symmetric_key)
    return _secure_channel(send, recv, cipher)


def secure_bob(send, recv):
    backend = backends.default_backend()
    onetime_public_key = serialization.load_ssh_public_key(recv(), backend=backend)
    cipher_name = 'AES256GCM'
    send(cipher_name.encode())
    cipher = make_cipher(cipher_name)
    send(onetime_public_key.encrypt(cipher.key, _OAEP_PADDING))
    return _secure_channel(send, recv, cipher)
