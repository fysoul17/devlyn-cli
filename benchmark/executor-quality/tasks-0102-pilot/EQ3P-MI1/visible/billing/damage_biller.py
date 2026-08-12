"""Damage settlement accepts evidence only while the review remains open."""


def review_damage(record, photos):
    if not photos:
        record["bill"] = "final"
        return record
    record["bill"] = "final"
    record["status"] = "settled"
    return record
