"""Serialization helpers for plain dictionaries."""


def pairs(values):
    return tuple(sorted(values.items()))
