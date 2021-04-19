import pickle

from creepy.types import SecureString
from creepy.utils.memory import secret_bytes_are_leaked


def test_secure_string_doesnt_leak():
    secret = SecureString()
    secret.append('P')
    secret.append('a')
    secret.append('s')
    secret.append('z')
    secret.append('w')
    secret.append('o')
    secret.append('r')
    secret.append('d')
    pickled_secret = pickle.dumps(secret)
    secret2 = pickle.loads(pickled_secret)
    assert secret == secret2
    secret2.append('2')
    assert secret != secret2
    assert not secret_bytes_are_leaked(secret)
    with secret:
        assert secret_bytes_are_leaked(secret)
    assert not secret_bytes_are_leaked(secret)


def test_secure_string_value():
    not_secret = b'Hello World!!!'
    secret = SecureString()
    for c in not_secret:
        secret.append_code(c)
    with secret as secret_mem:
        assert bytes(secret_mem) == not_secret


def test_secure_string_hash():
    secret = SecureString()
    for c in b'abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq':
        secret.append_code(c)
    assert secret.hash().hex() == '248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1'
