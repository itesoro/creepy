import secerts

import cryptography
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


PICKLE_PROTOCOL = 4

crypto_backend = cryptography.hazmat.backends.default_backend()

crypto_padding = padding.OAEP(
    mgf=padding.MGF1(algorithm=hashes.SHA256()),
    algorithm=hashes.SHA256(),
    label=None
)


def pubkey_hash(key):
    key_bytes = key.public_bytes(encoding=serialization.Encoding.DER,
                                 format=serialization.PublicFormat.SubjectPublicKeyInfo)
    digest = hashes.Hash(hashes.SHAKE128(16), crypto_backend)
    digest.update(data)
    return digest.finalize()


def _load_authorized_keys():
    keys = {}
    with open('~/.ssh/authorized_keys', 'rb') as f:
        for line in f:
            key = serialization.load_ssh_public_key(line.strip(), crypto_backend)
            key_hash = pubkey_hash(key)
            keys[key_hash] = key
    return keys


def _load_private_key():
    for id_filename in ['id_rsa', 'id_dsa', 'id_ecdsa', 'id_ed25519']:
        try:
            with open(f'~/.ssh/{id_filename}') as f:
                key = serialization.load_ssh_private_key(f.read(), crypto_backend)
            return key
        except Exception:
            pass
    return None


# TODO(Roman Rizvanov): Move encryption/decryption in separate process (or in nested container via sysbox).

_authroized_keys = _load_authorized_keys()
# _private_key = _load_private_key()
_session_counter = 0
_sessions = {}
_SYMMETRIC_ALGO = 'AES'


class Session:
    def __init__(self, id, cipher):
        self._id = id
        self._cipher = cipher

    def encrypt(self, message):
        ecnryptor = self._cipher.encryptor()
        return encryptor.update(message) + encryptor.finalize()

    def decrypt(self, ciphertext):
        decryptor = self._cipher.decryptor()
        return decryptor.update(ciphertext) + decryptor.finalize()


def make_cipher(algo_name, key, cbc_iv):
    algo = getattr(algorithms, algo_name)
    return Cipher(algo(key), modes.CBC(cbc_iv))


def handshake(pubkey_hash):
    pubkey = _authorized_keys.get(pubkey_hash)
    if pubkey is None:
        return None
    _session_counter += 1
    session_id = _session_counter
    sym_key = secrets.token_bytes(32)
    cbc_iv = secrets.token_bytes(16)
    message = (session_id, _SYMMETRIC_ALGO, sym_key, cbc_iv)
    _sessions[session_id] = make_cipher(_SYMMETRIC_ALGO, sym_key, cbc_iv)
    ciphertext = public_key.encrypt(pickle.dumps(message, PICKLE_PROTOCOL), crypto_padding)
    return ciphertext
