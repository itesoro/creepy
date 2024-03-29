import ctypes
from ctypes import c_void_p, c_size_t, c_int


# Edit '/etc/security/limits.conf' to change memory lock limits.

MCL_CURRENT = 1
MCL_FUTURE  = 2

try:
    _libc = ctypes.CDLL('libc.so.6', use_errno=True)
except:
    _libc = ctypes.CDLL('libc.dylib', use_errno=True)


def mlockall(flags: int = MCL_CURRENT | MCL_FUTURE):
    if _libc.mlockall(c_int(flags)) == 0:
        return
    raise OSError(ctypes.get_errno(), 'Cannot lock memmory')


def munlockall():
    if _libc.munlockall() == 0:
        return
    raise OSError(ctypes.get_errno(), 'Cannot unlock memmory')


def mlock(addr, size):
    if _libc.mlock(c_void_p(addr), c_size_t(size)) == 0:
        return
    raise OSError(ctypes.get_errno(), 'Cannot lock memmory')


def munlock(addr, size):
    if _libc.munlock(c_void_p(addr), c_size_t(size)) == 0:
        return
    raise OSError(ctypes.get_errno(), 'Cannot unlock memmory')
