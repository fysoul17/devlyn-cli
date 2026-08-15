"""Bonded release decision for a declaration preview."""


def can_request_release(preview):
    return preview["release_requested"] and not preview["errors"]


def release_message(preview):
    if can_request_release(preview):
        return "Release request accepted"
    return "Release request held for review"
