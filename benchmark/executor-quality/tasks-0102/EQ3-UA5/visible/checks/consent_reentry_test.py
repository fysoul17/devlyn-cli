"""Visible helpers for checking the returned desk receipt."""


def accepted(receipt):
    return receipt == {"accepted": True, "form": "v2"}
