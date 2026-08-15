"""Adjuster digest formatting."""


def digest_line(case):
    return f"{case['case_id']} {case['state']}"
