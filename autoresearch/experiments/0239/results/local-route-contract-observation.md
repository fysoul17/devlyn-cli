# Local-delivery interface: observation, not an admitted instruction

2026-10-10. The completed s01/s02 forced smokes both inspect task-complete.py
before delivery. The running ordinary d01 also queried configuration/Git
operations and read production helper sections (stdout1166–1175), after its
earlier source-contract/depth analysis. No d01 final outcome is available here.
These observations extend the question in0237/results/f01-helper-loading-audit.md;
they do not establish why all the inspection occurred or that it was needless.

The common caller permits Git internal metadata writes for worktrees/commits
but prohibits Git configuration changes. The public completion guide describes
local allocation and promises no fetch/push; it does not explicitly describe
configuration writes. The executed s01/s02 runs preserved the anchor Git
configuration, but those runs have ordinary fixture configuration and cannot
prove behavior for every installed hook or Git setup.

Static reading of the accepted helper (SHA256
60e101dd720348207a6001432a2b6f66f3c861846b1e768af5456804a402ac8a):

- allocate resolves an exact --local-base, marks local_only, skips the remote
  policy/URL path, and calls `git worktree add -b <branch> <path> <commit>`.
- Local completion binds source/acceptance custody and returns LOCAL_ONLY
  before publication policy and GitHub operations.
- The two literal production `config` invocations are reads in remote_url and
  policy. Many additional config matches belong to the embedded self-tests,
  which normal allocation/completion does not execute.

This identifies a public-interface question, not a demonstrated contract bug.
Any proposed documentation claim must distinguish helper-issued configuration
commands from Git's own metadata/config behavior and user hooks. Do not promise
that arbitrary hooks cannot change configuration; do not suppress a needed
inspection or change the caller restriction to improve a score. A generic
"read less helper source" clause still lacks a clear causal/safety prediction.

No product words, runtime, fixture, ongoing source or old verdict changed.
There is no new registered candidate or test here. All prior and current costs
remain whole; in particular d01's long analysis before helper inspection cannot
be assigned to that later read. Assess this question after the fixed lifetime
diagnostic without treating it as a measured efficiency gain.
