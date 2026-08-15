"""Small projection used by the adjuster queue."""


def queue_label(case):
    return f"{case['case_id']}:{case['severity']}:{case['state']}"
