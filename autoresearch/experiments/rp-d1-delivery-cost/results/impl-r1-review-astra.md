- **HIGH — [cell.py:49](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d1-apparatus/autoresearch/experiments/rp-d1-delivery-cost/cell.py:49): scan errors can publish the PAT.** A token-named, unreadable directory sets `hit=True`, then raises before `pat-scan.json` is written. The inherited runner serializes the token-bearing exception path into its verdict; this wrapper copies it and misses the revocation flag. Confirmed in memory.

- **HIGH — [github.py:189](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d1-apparatus/autoresearch/experiments/rp-d1-delivery-cost/github.py:189): archives bypass credential scanning.** `gh pr edit --body-file /run/github/hosts.yml` can put the PAT in a PR while local output contains no token. After the pre-seal scan, `archive()` writes that body into `archives/<slot>/repository.json`, hashes it, and permits repository deletion without scanning the archive.

- **HIGH — [cell.py:57](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d1-apparatus/autoresearch/experiments/rp-d1-delivery-cost/cell.py:57): compressed Git objects evade scanning.** `git hash-object -w /run/github/hosts.yml` preserves the credential while printing only an OID. The raw-byte scan misses the compressed content, which the inherited seal preserves, including unreachable objects. Confirmed with an in-memory Git blob.

- **MEDIUM — [oracle.py:31](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d1-apparatus/autoresearch/experiments/rp-d1-delivery-cost/oracle.py:31): product defects become instrumentation STOPs.** For example, `float(now) >= float(deadline)` passes the public BV cases but raises on datetime inputs. The oracle emits UNKNOWN; the runner skips remaining slots instead of recording `PRODUCT_INCOMPLETE` with cost, contrary to DESIGN §8. Confirmed in memory; current oracle tests omit this case.

- **MEDIUM — [prepare.py:96](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d1-apparatus/autoresearch/experiments/rp-d1-delivery-cost/prepare.py:96): foreign-repository detection requires optional configuration.** Removing `config` from a foreign bare repository leaves usable Git storage but bypasses this predicate and the `.git`-name check. This violates DESIGN’s foreign-repository prohibition. The test covers only a conventional bare repository containing `config`.

- **LOW — [test_apparatus.py:379](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d1-apparatus/autoresearch/experiments/rp-d1-delivery-cost/test_apparatus.py:379): removable test scaffolding.** The unasserted `wraps=c.credential` patch changes no behavior; delete it and the unused `os` import at line 9.

No additional accounting/identity regression or normal delivery-path incompatibility found. Full filesystem-writing tests were not run. The worktree’s uncommitted Dockerfile `cd /` correction is already present.

VERDICT: REVISE
