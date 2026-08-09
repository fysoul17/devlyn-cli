# Configuration validation contract

Bundle validation parses every document before applying configuration rules. If any document is malformed JSON, the bundle result is `{"ok": false, "error": "invalid_json"}` even when an earlier document also violates a configuration rule.

After all documents parse, configuration errors are reported in document order. A valid bundle returns the validated names in input order.
