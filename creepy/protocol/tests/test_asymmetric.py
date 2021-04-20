from creepy.utils.memory import secret_bytes_are_leaked
from .. import asymmetric


def test_generate_passphrase():
    assert asymmetric.generate_passphrase() != asymmetric.generate_passphrase()
    passphrase = asymmetric.generate_passphrase()
    with passphrase as passphrase_mem:
        assert len(passphrase_mem) >= 16
    assert not secret_bytes_are_leaked(passphrase)
