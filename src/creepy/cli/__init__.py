import os
import sys
import time
import shlex

import click


@click.group()
def app():
    pass


@app.command(context_settings={"ignore_unknown_options": True})
@click.argument('args', nargs=-1)
def run(args):
    cmd = shlex.join(['uvicorn', 'creepy:app'] + list(args))
    while True:
        start = time.time()
        return_code = os.system(cmd)
        if return_code != 0:
            sys.exit(return_code)
        duration = time.time() - start
        if duration < 1:
            time.sleep(1 - duration)
