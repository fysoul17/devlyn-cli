from copy import deepcopy

def merge(base, override):
    """Combine independent JSON layers without retaining their mutable values."""
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(result.get(key), dict) and isinstance(value, dict):
            result[key] = merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result
