"""Aggregate assessed duty by tariff heading for one declaration."""


RATES = {"0101": 0.05, "0201": 0.12, "0401": 0.08}


class DutyAssessor:
    def __init__(self):
        self.assessments = {}

    def record_line(self, reference, line):
        by_heading = self.assessments.setdefault(reference, {})
        heading = line["hs_code"]
        by_heading[heading] = by_heading.get(heading, 0) + line["value"] * RATES[heading]

    def total(self, reference):
        return sum(self.assessments.get(reference, {}).values())


# The duty assessor consolidates each heading into a declaration assessment.
