# Publication contract

Drafts contain exactly a non-empty `title` and a non-empty URL-safe `slug`. Destinations map channel names to the slugs already in use.

Publication planning validates the draft before evaluating any destination condition. Consequently, an invalid draft returns `{"error": "invalid_draft"}` even when its requested channel is missing or its slug is already occupied.

For a valid draft, a missing channel returns `{"error": "unknown_channel"}`, an occupied slug returns `{"error": "slug_taken"}`, and an available destination returns the selected channel and slug.
