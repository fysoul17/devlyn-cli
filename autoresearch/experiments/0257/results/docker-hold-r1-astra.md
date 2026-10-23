SHIP — the scoped fix is correct. In-memory checks confirmed the 60-second retry, no premature dispatch, and preserved identity-mismatch exception.

- **MEDIUM, existing — [driver.py:216](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0257-docker-hold/autoresearch/experiments/0257/driver.py:216):** Docker dying after successful load still crashes readiness: `image_identity()` conflates failed inspection with an actual mismatch.
- **MEDIUM, existing — [prepare.py:88](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0257-docker-hold/autoresearch/experiments/0257/prepare.py:88):** Docker dying after preflight can make the B-arm installer’s `docker run` raise through `dispatch()` and terminate the driver before owner launch.
- **MEDIUM, existing — [driver.py:113](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0257-docker-hold/autoresearch/experiments/0257/driver.py:113):** If the output volume remains full, logging the hold can itself raise `ENOSPC`.
- **LOW — [driver.py:212](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0257-docker-hold/autoresearch/experiments/0257/driver.py:212):** Permanent load failures, including corrupt archives, also keep holding. This can delay recognition of apparatus failure, but the reason remains visible and no invalid cell dispatches.

No files edited. Full suite not run under the read-only restriction.

