#!/usr/bin/env python3
"""Check failed key-rotation behavior for EQ-AF2."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType


INVARIANT = (
    "Key rotation commits as one state transition: if any rewrap callback raises, "
    "the active key, every ciphertext, and completed-rotation count remain exactly "
    "as they were before the call."
)


def load_keyring(workdir: Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, workdir / "keyring.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load keyring fixture")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def state_of(keyring: object) -> tuple[object, dict[str, str], object]:
    return (
        keyring.active_key,
        dict(keyring.secrets),
        keyring.completed_rotations,
    )


def prepared(module: ModuleType) -> object:
    keyring = module.Keyring("key-a")
    keyring.add("alpha", "cipher-a")
    keyring.add("beta", "cipher-b")
    return keyring


def head_failure(workdir: Path) -> bool:
    module = load_keyring(workdir, "fixture_af2_head")
    keyring = prepared(module)
    before = state_of(keyring)
    if not hasattr(keyring, "rotate_key"):
        return False

    def reject(name: str, ciphertext: str, old_key: str, new_key: str) -> str:
        raise RuntimeError("halt")

    try:
        keyring.rotate_key("key-b", reject)
    except (RuntimeError, TypeError):
        pass
    return state_of(keyring) == before


def late_failure(workdir: Path) -> bool:
    module = load_keyring(workdir, "fixture_af2_late")
    keyring = prepared(module)
    before = state_of(keyring)
    if not hasattr(keyring, "rotate_key"):
        return False

    def reject_late(name: str, ciphertext: str, old_key: str, new_key: str) -> str:
        if name == "beta":
            raise RuntimeError("halt")
        return f"{ciphertext}+{new_key}"

    try:
        keyring.rotate_key("key-b", reject_late)
    except (RuntimeError, TypeError):
        pass
    return state_of(keyring) == before


def main() -> None:
    workdir = Path(sys.argv[1]).resolve()
    print(
        json.dumps(
            {
                "manifestations": [
                    {
                        "id": "af2-head-stop",
                        "invariant": INVARIANT,
                        "passed": head_failure(workdir),
                    },
                    {
                        "id": "af2-late-stop",
                        "invariant": INVARIANT,
                        "passed": late_failure(workdir),
                    },
                ]
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
