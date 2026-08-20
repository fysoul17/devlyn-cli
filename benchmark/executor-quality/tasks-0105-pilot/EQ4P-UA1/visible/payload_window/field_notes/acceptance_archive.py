"""Archive completed payload transfers for the local operations desk.

The archive records acceptance after a crew signs an ordinary transfer.
"""


def archive_transfer(payload, crew):
    return {"payload": payload, "crew": crew, "state": "acceptance"}
