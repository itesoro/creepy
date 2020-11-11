import os
import json
import struct
import secrets
import datetime
from dataclasses import dataclass

import cryptography
from cryptography.hazmat import backends
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature

from .common import make_cipher


@dataclass
class Bob:
    public_key: object
    last_nonce: int = 0


class HandshakeProtocol:
    HASH_ALGORITHM = cryptography.hazmat.primitives.hashes.SHA512()
    _VERSION = 0
    _HI_ALICE_FORMAT = struct.Struct(f'!IQ{HASH_ALGORITHM.digest_size}s')
    _HI_BOB_FORMAT = struct.Struct('!s16p32s')
    TRANSPORT_CIPHER_NAME = 'AES256GCM'
    SIGN_PADDING = padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH)
    ENCRYPT_PADDING = padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)

    def __init__(self, authorized_keys_path=None):
        self.salt = secrets.token_bytes(self.HASH_ALGORITHM.digest_size)
        if authorized_keys_path is None:
            authorized_keys_path = '~/.ssh/authorized_keys'
        bobs = {}
        with open(os.path.expanduser(authorized_keys_path), 'rb') as f:
            for line in f:
                key = serialization.load_ssh_public_key(line.strip(), backends.default_backend())
                key_hash = self.pubkey_digest(key, self.salt)
                bobs[key_hash] = Bob(key)
        self._bobs = bobs

    @classmethod
    def _digest(cls, *args):
        digest = hashes.Hash(cls.HASH_ALGORITHM, backends.default_backend())
        for x in args:
            digest.update(str(x).encode())
        return digest.finalize()

    @classmethod
    def pubkey_digest(cls, key, salt):
        key_bytes = key.public_bytes(encoding=serialization.Encoding.DER,
                                     format=serialization.PublicFormat.SubjectPublicKeyInfo)
        return cls._digest(key_bytes, salt)

    @classmethod
    def _hi_digest(cls, message, salt):
        return cls._digest(message['nonce'], message['hash'], salt)

    @classmethod
    def hi_alice(cls, private_key, public_channel):
        salt = public_channel('/salt')
        message = cls._HI_ALICE_FORMAT.pack(
            cls._VERSION,
            cls._timestamp(),  # nonce
            cls.pubkey_digest(private_key.public_key(), salt)
        )
        message += private_key.sign(cls._digest(message), cls.SIGN_PADDING, cls.HASH_ALGORITHM)
        encrypted_response = public_channel('/hi', message)
        assert encrypted_response is not None
        response = private_key.decrypt(encrypted_response, cls.ENCRYPT_PADDING)
        session_id, cipher_name, cipher_key = cls._HI_BOB_FORMAT.unpack(response)
        print(session_id, cipher_name, cipher_key)
        return session_id, cipher_name.decode(), cipher_key

    def who_r_u(self, signed_message):
        message, signature = signed_message[:self._HI_ALICE_FORMAT.size], signed_message[self._HI_ALICE_FORMAT.size:]
        version, nonce, hash = self._HI_ALICE_FORMAT.unpack(message)
        if version != 0:
            raise ValueError('Unsupported version')
        bob = self._bobs.get(hash)
        if bob is None:
            raise ValueError("I don't know you")
        if not isinstance(nonce, int) or nonce <= bob.last_nonce:
            raise ValueError("Invalid nonce")
        try:
            bob.public_key.verify(signature, self._digest(message), self.SIGN_PADDING, self.HASH_ALGORITHM)
        except InvalidSignature:
            raise ValueError("Nice try, Chuck")
        bob.last_nonce = nonce
        return bob

    def hi_bob(self, bob, session_id):
        cipher = make_cipher(self.TRANSPORT_CIPHER_NAME)
        message = self._HI_BOB_FORMAT.pack(session_id, cipher.name.encode(), cipher.key)
        ciphertext = bob.public_key.encrypt(message, self.ENCRYPT_PADDING)
        return cipher, ciphertext

    @staticmethod
    def _timestamp() -> int:
        now = datetime.datetime.utcnow()
        return int((now - datetime.datetime(1970, 1, 1)).total_seconds() * 1000)
