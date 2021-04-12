from .app import App
from .connect import connect, Session


# TDOO(Roman Rizvanov): Implement `creepy.import_module(name, *, hash: str)` instead. Usage example:
#
# module.py:
# > def plus(x, y): return x + y
#
# client.py:
# > import creepy
# > module = creepy.import_module('module', hash=...)
# > print(module.plus('Hello ', 'World!!!'))
