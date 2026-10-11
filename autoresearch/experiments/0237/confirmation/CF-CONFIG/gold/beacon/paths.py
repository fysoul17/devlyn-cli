from pathlib import Path

def canonical(path, parent=None):
    path = Path(path)
    if parent is not None and not path.is_absolute():
        path = Path(parent) / path
    return path.resolve()
