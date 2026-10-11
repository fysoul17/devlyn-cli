import json
from .errors import ConfigError

def read_document(path, chain):
    try:
        # Opening and closing without reading is not a second document read.
        with path.open('rb'):
            pass
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ConfigError(path, chain, f'cannot read config ({exc})') from exc
    if not isinstance(data, dict) or set(data) - {'include', 'values'}:
        raise ConfigError(path, chain, 'document must contain only include and values')
    includes = data.get('include', [])
    values = data.get('values', {})
    if not isinstance(includes, list) or not all(isinstance(p, str) and p for p in includes):
        raise ConfigError(path, chain, 'include must be a list of nonempty paths')
    if not isinstance(values, dict):
        raise ConfigError(path, chain, 'values must be an object')
    return includes, values
