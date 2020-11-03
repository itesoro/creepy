from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

crypto_backend = cryptography.hazmat.backends.default_backend()

crypto_padding = padding.OAEP(
    mgf=padding.MGF1(algorithm=hashes.SHA256()),
    algorithm=hashes.SHA256(),
    label=None
)


def pubkey_hash(key):
    key_bytes = key.public_bytes(encoding=serialization.Encoding.DER,
                                 format=serialization.PublicFormat.SubjectPublicKeyInfo)
    digest = crypto_hashes.Hash(crypto_hashes.SHAKE128(16), crypto_backend)
    digest.update(data)
    return digest.finalize()


def _load_authorized_keys():
    keys = {}
    with open('~/.ssh/authorized_keys', 'rb') as f:
        for line in f:
            key = serialization.load_ssh_public_key(line.strip(), crypto_backend)
            key_hash = pubkey_hash(key)
            keys[key_hash] = key
            digest = crypto_hashes.Hash(crypto_hashes.SHAKE128(16), crypto_backend)
            digest.update(key_bytes)
            key_hash = digest.finalize()
            print(len(key_hash), key_hash)
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


# TODO(Roman Rizvanov): Move encryption/decryption in separate process.

_authroized_keys = _load_authorized_keys()
_private_key = _load_private_key()