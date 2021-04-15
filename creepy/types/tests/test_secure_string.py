import os
import sys
import subprocess

from creepy.types import SecureString


def int_hex(x):
    return int(x, 16)


def proc_maps():
    with open(f'/proc/self/maps') as f:
        for line in f:
            cols = line.strip().split()[:5]
            address, perms, offset, dev, inode = cols
            begin, end = map(int_hex, address.split('-'))
            if dev != '00:00':
                continue
            offset = int_hex(offset)
            if offset != 0:
                continue
            yield begin, (end - begin)


def self_memory_to_file(file):
    with open(f'/proc/self/mem', 'rb') as f:
        for offset, size in proc_maps():
            try:
                f.seek(offset, os.SEEK_SET)
                file.write(f.read(size))
            except Exception:
                continue


def find_secret():
    cmd = [
        sys.executable,
        os.path.join(os.path.dirname(__file__), 'find_secret.py')
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    self_memory_to_file(proc.stdin)
    try:
        proc.stdin.close()
    except BrokenPipeError:
        pass
    return proc.wait()


def test_secure_string():
    ss = SecureString()
    ss.append('P')
    ss.append('a')
    ss.append('s')
    ss.append('z')
    ss.append('w')
    ss.append('o')
    ss.append('r')
    ss.append('d')
    assert find_secret() == 0
    with ss as mv:
        assert find_secret() == 255
    assert find_secret() == 0
