# Offline apparatus validation — 2026-10-18

Scope: new files only in `autoresearch/experiments/rp-d6-claude-delivery/`.
No live model cells, counting requests, registry requests, repository
provisioning/publication/deletion, or commits were performed. Authentication
tests use synthetic identities. The original DESIGN and rendered gate remain
byte-identical to HEAD:

```text
DESIGN.md        5cab97b4aad9f139d50e64c3a9344fbb694cd1d3e3cfe02a436683485fab2603
rendered_gate.py 29c916fe6d0c95896813abcd7a636e25e2768e8a1719b1c5f4cf5ad49ee032ef
```

Under **No guesswork**, the predictions recorded before execution were:
the targeted pack/no-origin fixtures would pass while rejecting extra pack
changes and network Git setup; inherited rp-d4/rp-d5 suites would remain
green; the complete rp-d6 suite would pass after the review corrections.
The suites ran separately with the environment/import mode in
[README.md](README.md#offline-checks), bytecode and pytest cache disabled.

Final raw pytest result lines:

```text
rp-d6: 176 passed in 83.11s (0:01:23)
rp-d4: 268 passed, 18 subtests passed in 108.91s (0:01:48)
rp-d5: 195 passed in 88.22s (0:01:28)
```

Earlier targeted pack/local checks passed 24 tests; initial runtime checks
passed 31. After the last grading changes, targeted grading/decision checks
passed 113 tests before the final full rp-d6 run above. These subsets overlap
the suite totals and must not be added to them. CLI help for pack, stage,
runner and summary exited 0. Syntax and whitespace checks passed all 14
Python files, including the unchanged rendered gate. Git status confirmed
that no file outside the requested directory changed and no pre-existing
tracked file changed.

## Review and corrections

Two Astra cross-model review rounds examined the contract and adapters.
The final review reported no remaining HIGH finding and conditional SHIP
after the LOCAL_ONLY parser narrowing and regression fixtures passed. That
condition is satisfied by the final targeted and full suite results above.

The implemented corrections cover stable public-check identifiers through
summary aggregation; g06 raw anchor, index and retained-worktree preservation
in addition to its committed snapshot; sentinel preservation; and ambiguous
or negated LOCAL_ONLY reports. Guard commit proof uses the inherited,
hash-bound local-delivery result, so an unrelated local commit cannot qualify.
Under **Production ready**, uncertain publication history and prose remain
explicit adjudications; they cannot silently authorize adoption.

## Contract interpretations

- The user's exact three-path pack requirement governs. The candidate commit
  changes those three shipped paths; `.agents` is excluded from shipping and
  `bin/instruction-templates.json` is unchanged, despite DESIGN's broader
  Y-path paragraph. The frozen document was not edited.
- Guard suffix framing is one newline before and after the exact suffix;
  both body and full caller-contract hashes are bound. Other prompt bodies
  remain unchanged.
- g05 means exactly one post-allocation task commit. g05/g06 require that
  local commit to match the assessed source, using inherited delivery proof.
- Final repository state does not prove the historical absence of an action
  followed by deletion. Unknown publication facts and ambiguous claims need
  a bound reviewer witness. Severe regression has its own witness field,
  including the paired-X comparison required for a measured Y slot.
- Pending adjudication leaves the exact ordered decision visible but marks
  it provisional and disables adoption authorization. COMPLETE usage with
  missing wall evidence leaves cost unestablished and routes an otherwise
  eligible candidate to HOLD; incomplete usage routes to INCONCLUSIVE first.

These are offline apparatus checks, not an rp-d6 measurement result.
