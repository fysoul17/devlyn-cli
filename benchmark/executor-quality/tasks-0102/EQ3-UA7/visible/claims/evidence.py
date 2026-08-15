"""Evidence source formatting."""


def evidence_label(review):
    return f"{review['id']}:{review['confidence']}"
