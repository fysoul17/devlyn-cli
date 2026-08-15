"""Small helpers for the paper-form intake screen."""


def form_label(version):
    return f"Consent form {version}"


def is_version(value):
    return isinstance(value, str) and value.startswith("v")
