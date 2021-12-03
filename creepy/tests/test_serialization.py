import io

from creepy.serialization import load_private_key, dump_private_key
from creepy.utils.memory import secret_bytes_are_leaked
from creepy.protocol import asymmetric
from creepy.protocol.asymmetric import generate_private_key


def test_dump_private_key():
    f = io.BytesIO()
    key = generate_private_key()
    passphrase = dump_private_key(key, f)
    assert not secret_bytes_are_leaked(passphrase)


def test_load_private_key(tmpdir):
    private_key_path = tmpdir / 'id_rsa'
    private_key = generate_private_key()
    public_key = private_key.public_key()
    passphrase = dump_private_key(private_key, private_key_path)
    del private_key
    pt = b'KRKR ALLE XX FOLGENDES IST SOFORT BEKANNTZUGEBEN XX'
    ct = asymmetric.encrypt(public_key, pt)
    private_key = load_private_key(private_key_path, passphrase)
    assert private_key.decrypt(ct) == pt
    assert not secret_bytes_are_leaked(passphrase)
