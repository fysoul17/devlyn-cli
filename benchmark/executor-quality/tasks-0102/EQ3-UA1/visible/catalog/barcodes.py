"""Normalize identifiers scanned at the desk."""


def normalize(value):
    return value.replace(" ", "").upper()
