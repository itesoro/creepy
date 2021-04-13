import ctypes


MCL_CURRENT = 1
MCL_FUTURE  = 2

_libc = ctypes.CDLL('libc.so.6', use_errno=True)


def mlockall(flags: int = MCL_CURRENT | MCL_FUTURE):
    result = _libc.mlockall(flags)
    if result != 0:
        raise RuntimeError(f'Cannot lock memmory: errno={ctypes.get_errno()}')


def munlockall():
    result = _libc.munlockall()
    if result != 0:
        raise RuntimeError(f'Cannot unlock memmory: errno={ctypes.get_errno()}')
