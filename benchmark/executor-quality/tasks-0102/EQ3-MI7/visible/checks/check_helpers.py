"""Shared fixture assertions."""


def has_pass_id(result, pass_id):
    return result["pass_id"] == pass_id
