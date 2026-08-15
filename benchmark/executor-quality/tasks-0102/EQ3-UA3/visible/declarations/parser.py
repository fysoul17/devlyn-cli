"""Parse declaration lines before they enter the calculation ledger."""


def classify_line(raw_line):
    code = raw_line.get("hs_code", "")
    if code not in {"0101", "0201", "0401"}:
        return None, f"Unsupported HS code: {code}"
    return {"hs_code": code, "value": raw_line["value"]}, None


def submit_declaration(reference, raw_lines, assessor):
    preview = {
        "reference": reference,
        "accepted_lines": [],
        "errors": [],
        "release_requested": False,
    }
    for position, raw_line in enumerate(raw_lines, start=1):
        line, error = classify_line(raw_line)
        if error:
            preview["errors"].append({"line": position, "message": error})
            return preview
        preview["accepted_lines"].append(line)
        assessor.record_line(reference, line)
    preview["release_requested"] = True
    return preview
