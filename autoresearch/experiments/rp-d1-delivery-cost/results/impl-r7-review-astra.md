**HIGH — anchor damage can still be hidden** at [github.py:315](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d1-apparatus/autoresearch/experiments/rp-d1-delivery-cost/github.py:315). `assume-unchanged` or `skip-worktree` can suppress content/executable-bit changes while the index matches allocation. Both diffs then pass; existence and the unchanged submitted snapshot provide no protection. [Git documents these index flags](https://git-scm.com/docs/git-update-index).

Unsealed `.git/info/attributes` also retains content normalization; `--no-textconv` does not disable clean conversion. Fsmonitor/textconv are explicitly disabled, and upstream config sealing rejects injected filter configuration. [Git attributes documentation](https://git-scm.com/docs/gitattributes). Compare raw anchor content/type with only Git-mode normalization, retaining the staged comparison.

- **Ordinary damage:** regressions cover content, deletion, executable-bit and staged-only changes, plus accepting `0600`. Raw smoke evidence confirms identical manifest hashes with only `644 → 600`.
- **Smoke gating:** read-only in-memory execution confirmed either failed smoke blocks measured `o01`; continuation still requires deletion receipts and uses the current attempt.
- **Coverage:** continuation and measurement-gating regressions exist. Index-flag/attribute bypass regressions are missing. Filesystem-writing tests were inspected, not executed.

VERDICT: REVISE
