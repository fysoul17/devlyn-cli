# Harbor Event Utilities

`src.sanitize.sanitize` is the single redaction boundary shared by API and CLI
callers. Adapters serialize its result but do not own secret-key policy.
