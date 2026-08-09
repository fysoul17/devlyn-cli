"""Mutable campaign theme tokens."""

import re


class ThemeError(ValueError):
    pass


class Theme:
    def __init__(self, tokens: dict[str, str]):
        self.tokens = dict(tokens)
        self.version = 0

    def set_token(self, name: str, value: str) -> None:
        if name not in self.tokens:
            raise ThemeError(f"unknown token: {name}")
        if re.fullmatch(r"#[0-9a-fA-F]{6}", value) is None:
            raise ThemeError(f"invalid color: {value}")
        self.tokens[name] = value.lower()
        self.version += 1

    def replace_palette(self, updates: dict[str, str]) -> int:
        """Replace several existing color tokens."""
        raise NotImplementedError("palette replacement is not implemented")
