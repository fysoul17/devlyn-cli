# Export data contract

`last_seen` must use RFC 3339. Downstream consumers accept either UTC normalized values with a trailing `Z` or values preserving each source offset; the product choice between those two representations is still pending.
