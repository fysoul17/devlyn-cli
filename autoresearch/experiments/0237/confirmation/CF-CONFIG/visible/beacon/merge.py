def merge(base, override):
    """Combine an earlier layer with a later layer."""
    result = dict(base)
    result.update(override)
    return result
