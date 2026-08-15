"""Formatting for signature-log rows."""


def row(identifier, signed_at):
    return {"participant": identifier, "signed_at": signed_at}
