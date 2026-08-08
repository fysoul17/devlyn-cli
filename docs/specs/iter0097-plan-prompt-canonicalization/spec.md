---
complexity: medium
---

# iter-0097 — renderer canonicalization (no terminal LF) + cue sentence deletion

Adjudicated at the iter-0097 R0 round (2026-08-05, convergent Grok+Codex;
registration `autoresearch/iterations/0097-plan-prompt-canonicalization.md`
§ R0 adjudication). Trigger: DECISIONS 0096.1 — the identical one-byte
terminal-LF delivery strip recurred WITH the Read-cue instruction
in-tree (third occurrence of the class); the pre-named escalation from
the 0095 design round fires: fix the artifact, not the instruction.

## Requirements

### R1 — renderer canonicalization (`config/skills/_shared/phase-prompt-render.py`)

The renderer's output contract becomes "never emits a terminal LF": the
MAXIMAL trailing run of `0x0a` bytes is removed from the rendered bytes
before write and hash (`rendered = rendered.rstrip(b"\n")`); every
content-internal byte is preserved; no other normalization. The printed
digest remains the sha256 of exactly the bytes written. Self-test
additions (in-file): rendered output never ends with `0x0a` for inputs
whose concatenation ends with zero, one, and multiple terminal LFs;
digest equals the written bytes in each case; the existing
task-context-without-final-newline case stays green unchanged.

### R2 — cue sentence deletion (net-negative)

Delete this exact sentence (added by 8f99b51) from
`config/skills/devlyn:resolve/SKILL.md` PHASE 1 round-0 dispatch
paragraph: "In Read output, a final empty numbered line denotes the
file's terminal LF — reproduce that LF at the end of the `prompt`
field; if no empty numbered line appears, do not add one. " (one
sentence plus its single trailing space separator, restoring the
paragraph's pre-8f99b51 byte flow around it). With a canonicalized
artifact the cue can never appear; dead prose dilutes the load-bearing
instruction.

### R3 — mirrors

Synchronize both changed files to `.agents` and `.claude` mirrors
byte-identically in the same commit.

## Out of scope

- No digest/oracle/watcher/scorer changes; no other renderer behavior
  (header validation, fail-closed paths) touched.
- No other SKILL.md edits.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    {
      "cmd": "python3 config/skills/_shared/phase-prompt-render.py --self-test",
      "exit_code": 0,
      "timeout_sec": 120
    },
    {
      "cmd": "test \"$(grep -cF 'a final empty numbered line denotes' 'config/skills/devlyn:resolve/SKILL.md')\" = 0",
      "exit_code": 0
    },
    {
      "cmd": "diff -q config/skills/_shared/phase-prompt-render.py .agents/skills/_shared/phase-prompt-render.py && diff -q config/skills/_shared/phase-prompt-render.py .claude/skills/_shared/phase-prompt-render.py && diff -q 'config/skills/devlyn:resolve/SKILL.md' '.agents/skills/devlyn:resolve/SKILL.md' && diff -q 'config/skills/devlyn:resolve/SKILL.md' '.claude/skills/devlyn:resolve/SKILL.md'",
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
