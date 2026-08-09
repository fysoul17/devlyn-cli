# Catalog synchronization contract

`transport.classify_response` supplies decoded catalog items to `sync.CatalogSync.ingest`.

Catalog synchronization quarantines a syntactically malformed or structurally invalid response body without advancing its cursor or scheduling a retry, regardless of the response status.

A valid response body is a JSON object whose `items` value is a list of objects. A non-success response with a valid body represents an unavailable upstream.
