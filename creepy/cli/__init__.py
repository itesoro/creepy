import os
import time
import shlex

import click


@click.group()
def app():
    pass


@app.command(context_settings={"ignore_unknown_options": True})
@click.argument('additional-args', nargs=-1)
def start(additional_args):
    cmd = shlex.join(['uvicorn', 'creepy:app'] + list(additional_args))
    while os.system(cmd) == 0:
        time.sleep(1)
