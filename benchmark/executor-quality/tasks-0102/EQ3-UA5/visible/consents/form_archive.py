"""Archive labels for signed forms."""


def archive_key(identifier, version):
    return f"{identifier}:{version}"
