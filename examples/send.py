import re
import sys

import creepy


def usage():
    print(f'Usage: {sys.argv[0]} <src-path> <remote-host>:<port>/<dst-path>')
    quit()


def split_remote_path(path):
    match = re.search(r'^((\w+)://)?[a-zA-Z0-9_\.]+(:\d+)?/', path)
    if not match:
        usage()
    i = match.span()[1]
    return path[:i], path[i:]


if len(sys.argv) != 3:
    usage()

src_path = sys.argv[1]
host, dst_path = split_remote_path(sys.argv[2])

remote = creepy.connect(host)
remote.send(src_path, dst_path)
