"""Small record shapes used by the declaration desk."""


def new_line(hs_code, value):
    return {"hs_code": hs_code, "value": value}


def blank_preview(reference):
    return {"reference": reference, "accepted_lines": [], "errors": []}
