import ctypes
from ctypes import c_void_p, c_size_t, c_int


# Edit '/etc/security/limits.conf' to change memory lock limits.

MCL_CURRENT = 1
MCL_FUTURE  = 2

_libc = ctypes.CDLL('libc.so.6', use_errno=True)


def mlockall(flags: int = MCL_CURRENT | MCL_FUTURE):
    result = _libc.mlockall(c_int(flags))
    if result != 0:
        raise OSError(ctypes.get_errno(), 'Cannot lock memmory')


def munlockall():
    result = _libc.munlockall()
    if result != 0:
        raise OSError(ctypes.get_errno(), 'Cannot unlock memmory')


def mlock(addr, size):
    result = _libc.mlock(c_void_p(addr), c_size_t(size))
    if result != 0:
        raise OSError(ctypes.get_errno(), 'Cannot lock memmory')


def munlock(addr, size):
    result = _libc.munlock(c_void_p(addr), c_size_t(size))
    if result != 0:
        raise OSError(ctypes.get_errno(), 'Cannot unlock memmory')
