import re
import sys
from contextlib import ExitStack

import click
import creepy


def split_remote_path(path):
    match = re.search(r'^((\w+)://)?[a-zA-Z0-9_\.]+(:\d+)?:', path)
    if not match:
        return 'self', path
    i = match.span()[1]
    return path[:i - 1], path[i:]
    

@click.command()
@click.argument('src-path', type=str)
@click.argument('dst-path', type=str)
@click.option('-f', '--force', is_flag=True)
def main(src_path, dst_path, force):
    """
    Copy files or directories from one creepy node to another.
    SRC-PATH and DST_PATH must be in the following format:
    [<host>:<port>]:<path>
    """
    src_host, src_path = split_remote_path(src_path)
    dst_host, dst_path = split_remote_path(dst_path)
    with ExitStack() as exit_stack:
        src_node = exit_stack.enter_context(creepy.connect(src_host))
        dst_node = exit_stack.enter_context(creepy.connect(dst_host))
        creepy.copy(src_node.path(src_path), dst_node.path(dst_path), exist_ok=True, archive=True)


if __name__ == '__main__':
    main()
