---
id: agent-instructions-update-notice
title: Explain preservation of existing AGENTS instructions during updates
complexity: medium
changed_files:
  - bin/devlyn.js
  - README.md
---

# Explain preservation of existing AGENTS instructions during updates

## Problem and prediction

The published 3.0.0 package already includes the current AGENTS.md and CLAUDE.md.
Existing marker-free AGENTS.md is preserved by `installInstructionsForCLI`, while
`installClaudeCore` replaces CLAUDE.md. The current installer silently skips the
AGENTS write, and README's “Run it again anytime to update” does not explain this.
Prediction: the normal update reports preservation and a usable current-template
path while keeping existing AGENTS bytes unchanged and refreshing selected skills.

## Requirements

1. When the existing AGENTS.md has no legacy managed marker and is not rewritten,
   print a concise notice that it was preserved. Point to the bundled current
   AGENTS.md template so the user can compare and merge relevant instructions.
   Do not claim the file is outdated: an identical current file follows this path.
2. Qualify README's update guidance: selected skills refresh; existing AGENTS.md
   is preserved, whereas the selected Claude installer replaces CLAUDE.md.
   Explain comparison/merging of shared runtime instructions into preserved AGENTS.
3. Preserve missing-file creation, existing legacy-marker stripping, target
   selection and customer content. Keep engine-specific instructions distinct.
   Do not add a flag, migration, overwrite policy, dependency, abstraction or
   automated test file. AGENTS.md/CLAUDE.md source content needs no change here.
4. Limit implementation to bin/devlyn.js and README.md. No version bump,
   publication, research context in customer instructions, or measured-run changes.

## Verification

Run the commands in spec.expected.json after implementation. Additionally, use
an actual package and normal installer in fresh owned temporary project/home
directories with the existing Node `os.homedir` preload; do not use customer homes.
Record exact commands, exit codes, stdout/stderr and before/after file bytes:

- Missing AGENTS: installed bytes exactly match the packaged source template.
- Custom marker-free AGENTS: exact bytes preserved; notice and template path shown.
- Current marker-free AGENTS: exact bytes preserved; same truthful notice shown.
- Legacy-marker AGENTS: existing stripping result unchanged; do not report the
  untouched-file notice when that legacy cleanup actually writes the file.
- Confirm the notice's template exists and matches packaged AGENTS; selected skills
  still install. Package AGENTS.md and CLAUDE.md must both match source bytes.

These installer checks are mandatory acceptance evidence in addition to syntax
and full skill lint. Use temporary commands, not a committed test harness.
Do not execute validation or installation during the active measured cohort.
