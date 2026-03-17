#!/usr/bin/env python3
"""Validate .dokkit/state.json against the Dokkit state schema.

Usage:
    python validate_state.py <path-to-state.json>

Exit codes:
    0 — valid
    1 — validation errors found
    2 — file not found or invalid JSON
"""

import json
import sys
from pathlib import Path


VALID_SOURCE_STATUSES = {"processing", "ready", "error"}
VALID_DOC_STATUSES = {"filling", "review", "modified", "finalized"}
VALID_FILE_TYPES = {
    "pdf", "docx", "xlsx", "csv", "pptx", "hwp", "hwpx",
    "png", "jpg", "jpeg", "txt", "md", "json", "html"
}
VALID_TEMPLATE_TYPES = {"docx", "hwpx"}
VALID_EXPORT_FORMATS = {"docx", "hwpx", "pdf"}


def validate(state: dict) -> list[str]:
    """Validate state dict, return list of error messages."""
    errors = []

    # Root fields
    if not isinstance(state.get("version"), str):
        errors.append("Missing or invalid 'version' (expected string)")
    if not isinstance(state.get("created"), str):
        errors.append("Missing or invalid 'created' (expected ISO timestamp string)")
    if not isinstance(state.get("sources"), list):
        errors.append("Missing or invalid 'sources' (expected array)")
    if "template" not in state:
        errors.append("Missing 'template' field (expected object or null)")
    if "analysis" not in state:
        errors.append("Missing 'analysis' field (expected object or null)")
    if "filled_document" not in state:
        errors.append("Missing 'filled_document' field (expected object or null)")
    if not isinstance(state.get("exports"), list):
        errors.append("Missing or invalid 'exports' (expected array)")

    # Validate sources
    for i, src in enumerate(state.get("sources", [])):
        prefix = f"sources[{i}]"
        for field in ("id", "file_path", "file_type", "display_name",
                       "content_path", "metadata_path", "summary", "status"):
            if not isinstance(src.get(field), str):
                errors.append(f"{prefix}: missing or invalid '{field}'")
        if src.get("status") and src["status"] not in VALID_SOURCE_STATUSES:
            errors.append(f"{prefix}: invalid status '{src['status']}' "
                          f"(expected one of {VALID_SOURCE_STATUSES})")
        if src.get("file_type") and src["file_type"] not in VALID_FILE_TYPES:
            errors.append(f"{prefix}: unknown file_type '{src['file_type']}'")

    # Validate template
    tmpl = state.get("template")
    if tmpl is not None:
        for field in ("file_path", "file_type", "display_name", "work_dir"):
            if not isinstance(tmpl.get(field), str):
                errors.append(f"template: missing or invalid '{field}'")
        if tmpl.get("file_type") and tmpl["file_type"] not in VALID_TEMPLATE_TYPES:
            errors.append(f"template: invalid file_type '{tmpl['file_type']}' "
                          f"(expected one of {VALID_TEMPLATE_TYPES})")

    # Validate analysis
    analysis = state.get("analysis")
    if analysis is not None:
        if not isinstance(analysis.get("path"), str):
            errors.append("analysis: missing or invalid 'path'")
        for field in ("total_fields", "mapped", "unmapped"):
            if not isinstance(analysis.get(field), int):
                errors.append(f"analysis: missing or invalid '{field}' (expected integer)")

    # Validate filled_document
    doc = state.get("filled_document")
    if doc is not None:
        if not isinstance(doc.get("status"), str):
            errors.append("filled_document: missing or invalid 'status'")
        elif doc["status"] not in VALID_DOC_STATUSES:
            errors.append(f"filled_document: invalid status '{doc['status']}' "
                          f"(expected one of {VALID_DOC_STATUSES})")

    # Validate exports
    for i, exp in enumerate(state.get("exports", [])):
        prefix = f"exports[{i}]"
        for field in ("format", "output_path"):
            if not isinstance(exp.get(field), str):
                errors.append(f"{prefix}: missing or invalid '{field}'")
        if exp.get("format") and exp["format"] not in VALID_EXPORT_FORMATS:
            errors.append(f"{prefix}: invalid format '{exp['format']}' "
                          f"(expected one of {VALID_EXPORT_FORMATS})")

    return errors


def main():
    if len(sys.argv) != 2:
        print("Usage: python validate_state.py <path-to-state.json>", file=sys.stderr)
        sys.exit(2)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Error: File not found: {path}", file=sys.stderr)
        sys.exit(2)

    try:
        with open(path, encoding="utf-8") as f:
            state = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(2)

    errors = validate(state)

    if errors:
        print(f"Validation FAILED — {len(errors)} error(s):", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)
    else:
        print("Validation passed.", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
