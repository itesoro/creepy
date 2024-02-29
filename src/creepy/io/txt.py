import os


def try_load_txt(path, default=None):
    if not os.path.isfile(path):
        return default
    try:
        with open(path, 'r') as f:
            return f.read()
    except Exception:
        return default


def dump_txt(path, data):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            f.write(data)
        return True
    except Exception:
        return False
