import os
import logging


logger = logging.getLogger('creepy')


def _copy_file(src_node, dst_node, src_path: str, dst_path: str, exist_ok=False):
    CHUNK_SIZE = 2**24
    if not exist_ok and dst_node.os.path.exists(dst_path):
        raise OSError(f"Path exists: '{dst_node}/{dst_path}'")
    with dst_node.open(dst_path, 'wb') as dst_f:
        with src_node.open(src_path, 'rb') as src_f:
            while True:
                chunk = src_f.read(CHUNK_SIZE)
                if not chunk:
                    break
                n = CHUNK_SIZE
                for i in reversed(range(4)):
                    try:
                        while True:
                            dst_f.write(chunk[:n])
                            if len(chunk) <= n:
                                break
                            chunk = chunk[n:]
                        break
                    except Exception as e:
                        logger.exception(e)
                        if i == 0:
                            raise
                        n /= 2


def _copy_directory(src_node, dst_node, src_dir: str, dst_dir: str, exist_ok=False):
    src_os = src_node.os
    dst_os = dst_node.os
    dst_os.makedirs(dst_dir, exist_ok=exist_ok)
    for src_root, dirs, files in src_os.walk(src_dir):
        dst_root = os.path.join(dst_dir, os.path.relpath(src_root, src_dir))
        for name in files:
            _copy_file(src_node, dst_node, os.path.join(src_root, name), os.path.join(dst_root, name))
        for name in dirs:
            dst_os.makedirs(os.path.join(dst_root, name), exist_ok=exist_ok)


def copy(src_path, dst_path, exist_ok, archive):
    src_node, src_path = src_path
    dst_node, dst_path = dst_path
    src_os = src_node.os
    dst_os = dst_node.os
    src_path = src_os.path.abspath(src_os.path.expanduser(src_path))
    if archive and src_os.path.isdir(src_path):
        src_tempfile = src_node.import_module('tempfile')
        dst_tempfile = dst_node.import_module('tempfile')
        src_shutil = src_node.import_module('shutil')
        dst_shutil = dst_node.import_module('shutil')
        ARCHIVE_FORMAT = 'gztar'
        if not exist_ok and dst_os.path.exists(dst_path):
            raise OSError(f"Path exists: '{dst_node}/{dst_path}'")
        with src_tempfile.TemporaryDirectory() as src_tmp_dir:
            with dst_tempfile.TemporaryDirectory() as dst_tmp_dir:
                src_archive_path = src_shutil.make_archive(
                    os.path.join(src_tmp_dir, 'temp'),
                    ARCHIVE_FORMAT,
                    src_path
                )
                dst_archive_path = os.path.join(
                    dst_tmp_dir._get(),
                    os.path.basename(src_archive_path)
                )
                _copy_file(src_node, dst_node, src_archive_path, dst_archive_path, exist_ok=False)
                dst_shutil.unpack_archive(dst_archive_path, dst_path, format=ARCHIVE_FORMAT)
        return
    if src_os.path.isfile(src_path):
        return _copy_file(src_node, dst_node, src_path, dst_path, exist_ok)
    return _copy_directory(src_node, dst_node, src_path, dst_path, exist_ok)