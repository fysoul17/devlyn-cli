"""In-memory ciphertext keyring."""

from __future__ import annotations

from typing import Callable


Rewrapper = Callable[[str, str, str, str], str]


class Keyring:
    """Store named ciphertexts under one active key."""

    def __init__(self, active_key: str) -> None:
        self.active_key = active_key
        self.secrets: dict[str, str] = {}
        self.completed_rotations = 0

    def add(self, name: str, ciphertext: str) -> None:
        """Store a new named ciphertext."""
        if name in self.secrets:
            raise ValueError(f"secret already exists: {name}")
        self.secrets[name] = ciphertext
