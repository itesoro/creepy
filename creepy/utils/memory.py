import os

from creepy.types import SecureString


def _proc_maps():
    def int_hex(x): return int(x, 16)
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


def secret_bytes_are_leaked(secret: SecureString):
    with open(f'/proc/self/mem', 'rb') as f:
        memory_regions = _proc_maps()
        cpid = os.fork()
        if cpid == 0:
            secret_mv = secret.__enter__()
            for offset, size in memory_regions:
                try:
                    f.seek(offset, os.SEEK_SET)
                    mem_region = f.read(size)
                    if mem_region.find(secret_mv) != -1:
                        os._exit(1)
                except Exception:
                    continue
            os._exit(0)
        _, exit_code = os.waitpid(cpid, 0)
        return bool(exit_code)
