from pathlib import Path

from flask import abort


def secure_path(path):
    root = Path(".").resolve()
    full_path = root / path
    if root not in full_path.parents:
        abort(403)
    return full_path
