"""Layer configuration dictionaries."""


def merge_layers(*layers):
    result = {}
    for layer in layers:
        result.update(layer)
    return result
