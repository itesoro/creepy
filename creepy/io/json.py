import os
import json


def try_load_json(path, default=None):
    if not os.path.isfile(path):
        return default
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception:
        return default


def dump_json(path, data, *args, **kwargs):
    with open(path, 'w') as f:
        json.dump(data, f, *args, **kwargs)
