def merge(base, override):
    """Do not mutate either input; internal subtrees may be shared."""
    result = dict(base)
    for key, value in override.items():
        before = result.get(key)
        if isinstance(before, dict) and isinstance(value, dict):
            result[key] = merge(before, value)
        else:
            result[key] = value
    return result
