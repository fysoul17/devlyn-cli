---
complexity: medium
---

# iter-0095 — Claude PLAN-delivery terminal-LF instruction

Design round held 2026-08-05 (Fable orchestrator + Codex gpt-5.6-sol;
receipts `~/.local/share/nx01/iter0095-design/`). The orchestrator's
"invisible byte → fix the artifact" position was refuted by its own
precommitted falsifier F2: Claude Code's Read output DOES represent a
file's terminal LF as a final empty numbered line (verified in both
retained 0094 sessions plus a no-LF control). Adopted synthesis, named
criterion OBSERVABLE RECEIPT INTEGRITY: keep the byte-exact digest gate
and the 0094 verdict; the smallest change is a one-sentence
delivery-instruction amendment. iter-0094 terminal evidence
(DECISIONS 0094.1): candidate-discovery delivered the rendered PLAN
prompt minus its single terminal LF (10,015 vs 10,016 bytes) while
candidate-simple delivered byte-exact through the identical
Read→transcribe route — the failing parent saw the cue and did not
reproduce it.

## Requirements

### R1 — one-sentence delivery-instruction amendment

In `config/skills/devlyn:resolve/SKILL.md`, PHASE 1 round-0 PLAN
dispatch paragraph (the "In Claude Code, invoke the native `Agent`…"
sentence region), insert exactly this sentence immediately after the
sentence ending "…any variable-reference substitution is not the
rendered prompt.":

> In Read output, a final empty numbered line denotes the file's
> terminal LF — reproduce that LF at the end of the `prompt` field; if
> no empty numbered line appears, do not add one.

(As one sentence on the same line-flow as the surrounding paragraph;
the round-1 corrective re-spawn already references "the same native
call shape as round 0" and needs no separate copy.)

### R2 — mirror synchronization

Synchronize the changed `config/skills/devlyn:resolve/SKILL.md` to the
tracked `.agents/skills/devlyn:resolve/SKILL.md` and the ignored
installed `.claude/skills/devlyn:resolve/SKILL.md` in the same commit —
the live parent executes installed bytes, so mirror identity is what
makes the next live matrix exercise the amended instruction.

## Out of scope

- No renderer change (`phase-prompt-render.py` untouched); no digest,
  state, or oracle change; no normalization layer anywhere.
- No change to the Codex CLI / oh-my-pi delivery routes (the failure
  class is the Claude Read→transcribe route only).
- No new flags, no adapter-file edits, no other-phase edits.
- Artifact canonicalization (renderer emitting no terminal LF) is a
  pre-named successor path ONLY if a live 2/2 bar still fails with the
  explicit cue — not this change.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    {
      "cmd": "test \"$(grep -cF 'a final empty numbered line denotes' 'config/skills/devlyn:resolve/SKILL.md')\" = 1",
      "exit_code": 0
    },
    {
      "cmd": "grep -qF 'reproduce that LF at the end of the `prompt` field; if no empty numbered line appears, do not add one' 'config/skills/devlyn:resolve/SKILL.md'",
      "exit_code": 0
    },
    {
      "cmd": "diff -q 'config/skills/devlyn:resolve/SKILL.md' '.agents/skills/devlyn:resolve/SKILL.md' && diff -q 'config/skills/devlyn:resolve/SKILL.md' '.claude/skills/devlyn:resolve/SKILL.md'",
      "exit_code": 0
    },
    {
      "cmd": "bash scripts/lint-skills.sh",
      "exit_code": 0,
      "timeout_sec": 300
    },
    {
      "cmd": "git diff --check",
      "exit_code": 0
    }
  ],
  "max_deps_added": 0
}
```
