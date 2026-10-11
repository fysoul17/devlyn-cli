import json

def write(root, name, *, include=None, values=None):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if include is not None:
        data['include'] = include
    if values is not None:
        data['values'] = values
    path.write_text(json.dumps(data), encoding='utf-8')
    return path
