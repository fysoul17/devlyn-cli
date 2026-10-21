No HIGH, MEDIUM, or LOW findings.

- [prepare.py:115](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0256-package-replay/autoresearch/experiments/0256/prepare.py:115) fixes the root invariant: canonicalizes tracked regular-file modes, preserves symlinks, and rejects remaining tracked-entry differences. The unconditional call covers A/B and Claude/Codex; `baseline.json` reuses the same committed mapping.
- Receipt snapshots already use canonical Git modes; anchor snapshots now preserve matching working-tree modes. Normalization occurs before participant execution. DESIGN.md’s grading contract and 0233’s snapshot selection and scope comparison remain unchanged; the fix introduces no exemption that hides participant changes.
- [test_apparatus.py:43](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0256-package-replay/autoresearch/experiments/0256/test_apparatus.py:43) checks 0600→0644, preserved 0755, and tree equality; the following test requires rejection of changed content. A no-op helper would fail both tests.

One read-only cross-model review round completed. Test failure behavior was verified by inspection; pytest was not rerun.

SHIP
