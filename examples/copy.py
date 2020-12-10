import re
import sys
from contextlib import ExitStack

import creepy


def usage():
    print(f'Usage: {sys.argv[0]} <src-path> <remote-host>:<port>/<dst-path>')
    quit(-1)


def split_remote_path(path):
    match = re.search(r'^((\w+)://)?[a-zA-Z0-9_\.]+(:\d+)?/', path)
    if not match:
        return 'self', path
    i = match.span()[1]
    return path[:i - 1], path[i:]


if len(sys.argv) != 3:
    usage()

src_host, src_path = split_remote_path(sys.argv[1])
dst_host, dst_path = split_remote_path(sys.argv[2])

with ExitStack() as exit_stack:
    src_node = exit_stack.enter_context(creepy.connect(src_host))
    dst_node = exit_stack.enter_context(creepy.connect(dst_host))
    creepy.copy(src_node.path(src_path), dst_node.path(dst_path), exist_ok=True, archive=True)
