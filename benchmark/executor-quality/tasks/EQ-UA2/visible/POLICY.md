# Artifact access policy

Catalog entries describe release artifacts, while grants decide which callers may read them.

The `retrieve` operation authorizes the caller's `read` grant before consulting catalog membership. A caller without that grant receives `{"error": "access_denied"}` for every requested key, so catalog presence is not disclosed.

After authorization succeeds, an absent key returns `{"error": "not_found"}`. A successful lookup returns the requested key and its artifact metadata.
