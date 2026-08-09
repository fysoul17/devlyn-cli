"""Syntax checks for normalized DNS record changes."""

import ipaddress


SUPPORTED_TYPES = {"A", "AAAA", "CNAME", "TXT"}


def syntax_issues(change: dict) -> list[str]:
    issues: list[str] = []
    owner = change["owner"]
    if not isinstance(owner, str) or not owner.endswith(".") or " " in owner:
        issues.append("owner")

    record_type = change["type"]
    if record_type not in SUPPORTED_TYPES:
        issues.append("type")

    value = change["value"]
    if not _valid_value(record_type, value):
        issues.append("value")
    return issues


def _valid_value(record_type: object, value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    if record_type == "A":
        try:
            return ipaddress.ip_address(value).version == 4
        except ValueError:
            return False
    if record_type == "AAAA":
        try:
            return ipaddress.ip_address(value).version == 6
        except ValueError:
            return False
    if record_type == "CNAME":
        return value.endswith(".") and " " not in value
    if record_type == "TXT":
        return len(value) <= 255
    return False
