import io

from creepy.utils.memory import secret_bytes_are_leaked
from creepy.protocol.asymmetric import generate_private_key


def test_dump_private_key():
    from creepy.serialization import dump_private_key
    f = io.BytesIO()
    key = generate_private_key()
    passphrase = dump_private_key(key, f)
    assert not secret_bytes_are_leaked(passphrase)
    with passphrase:
        assert secret_bytes_are_leaked(passphrase)
    assert not secret_bytes_are_leaked(passphrase)
