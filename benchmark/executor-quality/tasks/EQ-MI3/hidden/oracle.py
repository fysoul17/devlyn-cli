#!/usr/bin/env python3
"""Check the hidden behavioral manifestations for EQ-MI3."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType


INVARIANT = (
    "Bundle validation reports malformed JSON before any configuration-rule error, "
    "regardless of which document contains either defect."
)


def load_validator(workdir: Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        module_name, workdir / "config_validator.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load configuration fixture")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def has_syntax_result(result: object) -> bool:
    expected = "invalid" + "_" + "json"
    return (
        isinstance(result, dict)
        and result.get("ok") is False
        and result.get("error") == expected
    )


def syntax_leading(workdir: Path) -> bool:
    validator = load_validator(workdir, "fixture_leading")
    valid = json.dumps({"name": "edge", "routes": ["/ping"]})
    try:
        result = validator.validate_bundle(["{", valid])
    except (AttributeError, TypeError):
        return False
    return has_syntax_result(result)


def syntax_after_semantic(workdir: Path) -> bool:
    validator = load_validator(workdir, "fixture_later")
    duplicate = json.dumps({"name": "edge", "routes": ["/x", "/x"]})
    try:
        result = validator.validate_bundle([duplicate, "{"])
    except (AttributeError, TypeError):
        return False
    return has_syntax_result(result)


def main() -> None:
    workdir = Path(sys.argv[1]).resolve()
    print(
        json.dumps(
            {
                "manifestations": [
                    {
                        "id": "syntax-leading",
                        "invariant": INVARIANT,
                        "passed": syntax_leading(workdir),
                    },
                    {
                        "id": "syntax-after-semantic",
                        "invariant": INVARIANT,
                        "passed": syntax_after_semantic(workdir),
                    },
                ]
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
