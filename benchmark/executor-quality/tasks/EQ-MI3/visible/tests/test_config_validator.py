from __future__ import annotations

import json
import unittest

import config_validator


class ConfigValidatorTests(unittest.TestCase):
    def test_accepts_valid_document(self) -> None:
        text = json.dumps({"name": "public", "routes": ["/", "/health"]})

        self.assertEqual(
            config_validator.validate_document(text),
            {"ok": True, "name": "public"},
        )

    def test_rejects_duplicate_route(self) -> None:
        text = json.dumps({"name": "admin", "routes": ["/jobs", "/jobs"]})

        self.assertEqual(
            config_validator.validate_document(text),
            {"ok": False, "error": "duplicate_route"},
        )

    def test_rejects_malformed_json(self) -> None:
        self.assertEqual(
            config_validator.validate_document("{"),
            {"ok": False, "error": "invalid_json"},
        )


if __name__ == "__main__":
    unittest.main()
