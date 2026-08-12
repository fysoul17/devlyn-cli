"""Common assertions for the front-counter flow."""


def rejected(receipt):
    return receipt == {"accepted": False, "renewed": True}
