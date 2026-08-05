---
complexity: medium
---

# iter-0098 prereq — recert chain exact Claude model-ID support

Trigger: 2026-07-28 diagnosis (memory `opus5-seat-uncertified-diagnosis`;
HANDOFF frontier): the prescribed claude-opus-4-8 vs claude-opus-5 seat
A/B is impossible without instrument extension — `recert-seats.sh`
accepts only `sonnet|opus|codex` aliases, judge-quality hardcodes
`--model sonnet`, and two aggregator regexes silently drop hyphenated
model tokens. Queue item "Context-engineering item 2 of 2"
(docs/specs/queue.md) names this as its PREREQUISITE: exact pinned
identities claude-opus-4-8 (gen-4) + claude-opus-5 (gen-5) must be
certifiable per exact model ID, not CLI-default alias.

Already exact-ID capable, DO NOT TOUCH: `run-drift-bait-probe.sh`,
`run-drift-bait-probe-resolve.sh`, `run-compliance-cell.sh` (all take
`MODEL=<alias|full-name>` → `--model` passthrough), and
`run-violation-matrix.sh` (csv → MODEL env; model token embedded in
run-id).

## Requirements

### R1 — `benchmark/seats/recert-seats.sh` exact-ID engines

- Engine tokens: existing `sonnet`, `opus`, `codex` unchanged; ADD any
  token matching `^claude-[A-Za-z0-9.-]+$` as an exact Claude model ID.
- Every Claude engine token (alias or exact ID) routes to: violation
  suite via `run-violation-matrix.sh --models` (as aliases do today),
  compliance suite via `MODEL=<token> ... --cli claude`, and the
  judge_quality suite as a claude judge token. The judge routing is the
  named diagnosis fix: today only `sonnet` joins JUDGES ("JUDGES에서
  opus 제외"); after this change `opus` and exact claude IDs join too.
- `ENGINE_VERSIONS` maps every Claude token to
  `"<claude --version>/<token>"`; codex mapping unchanged.
- Unknown engine tokens still fail closed (nonzero exit, "unsupported
  engine") BEFORE any suite executes (current parse-before-suites
  ordering preserved so a skip-all smoke run exercises validation
  without spawning engines).

### R2 — `benchmark/probes/judge-quality/run_judge_quality.py` claude judge generalization

- Generalize the hardcoded sonnet route (`call_sonnet`, `--model
  sonnet` at :133) into a claude judge route parameterized by model:
  `--model <judge token>`. Accepted claude judge tokens: `sonnet`
  (behavior byte-identical to today), `opus`, and exact
  `^claude-[A-Za-z0-9.-]+$` IDs.
- Fail-closed judge validation at startup, applied to `--dry-run` too:
  allowed judges are `ollama`, `codex`, and the claude tokens above;
  anything else exits nonzero (argparse error) before any engine call.
- `write_identity` for claude judges records
  `model_id_or_alias=<judge token>` (currently hardcoded `"sonnet"`).
- Per-judge results dir keeps the judge token as its name (existing
  keying) so seat-matrix attribution passes the token through
  unchanged.

### R3 — `benchmark/seats/seat-matrix.py` hyphen-safe attestation

- `collect_attested_drift_cells`: replace the `DRIFT_RUN_ID_RE` global
  parse (model group `[A-Za-z0-9_.]+` excludes `-`; greedy prefix makes
  `<prefix>-violation-claude-opus-4-8-r1` fail the prefix equality
  check and drop silently) with prefix-anchored parsing: dir name must
  start with `{attest_run_prefix}-violation-` and end with
  `-r<digits>`; the remainder between them is the model token, hyphens
  permitted. Legacy alias dirs parse identically to today.
- `alias_from_attested_artifact`: replace the single-`-`-token
  membership test (which can never match a hyphenated alias like
  `claude-opus-5`) with prefix-anchored matching: for a path part
  starting with `{attest_run_prefix}-`, an alias matches when the
  remainder equals the alias or starts with `<alias>-`; on multiple
  matches choose the longest alias; no match → `None` (fail-closed).
- Add `--self-test` (temp-dir only, zero repo writes) covering at
  minimum: hyphenated attested drift dir → `drift_resistance` cell
  with `engine_alias=claude-opus-4-8` and status `current`; legacy
  `opus` attested dir → cell unchanged vs today; compliance artifact
  under `<prefix>-claude-opus-5-compliance/` → engine_alias
  `claude-opus-5`; non-matching dir names yield no attested cells.

### R4 — `benchmark/probes/scripts/violation-rate-matrix.py` hyphen-safe run-id parse

- `RUN_ID_RE` (model group `[A-Za-z0-9.]+`, same silent-drop class as
  R3) replaced by the same prefix-anchored scheme: `--run-prefix`
  anchored exactly, `-r<digits>` suffix, hyphen-capable model token
  between. Legacy non-hyphen run-ids aggregate identically.
- Add `--self-test` (temp-dir only) with one hyphenated-model case and
  one legacy-alias case asserting cell/totals equivalence.

### R5 — `.gitignore` run-state parity

Add `benchmark/seats/results/` (recert-status.json run state). The
other four benchmark results roots are already gitignored
(.gitignore:25,31,35,39-45); this one missing means every certification
run leaves untracked files that contaminate the scope baseline of any
subsequent pipeline run in this repo (the iter-0096 concurrent-edit
contamination class).

## Out of scope

- No changes to the probe/compliance runner scripts named above as
  already exact-ID capable.
- No skill, CLAUDE.md, AGENTS.md, or adapter edits; no seat re-pinning;
  no new engine families beyond the claude-token validation.
- No change to which suites run per engine beyond the named JUDGES
  generalization.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    {
      "cmd": "bash -n benchmark/seats/recert-seats.sh",
      "exit_code": 0,
      "timeout_sec": 30
    },
    {
      "cmd": "python3 benchmark/probes/judge-quality/run_judge_quality.py --dry-run --judges claude-opus-4-8,claude-opus-5,codex",
      "exit_code": 0,
      "timeout_sec": 30
    },
    {
      "cmd": "python3 benchmark/probes/judge-quality/run_judge_quality.py --dry-run --judges bogus-judge",
      "exit_code": 2,
      "timeout_sec": 30
    },
    {
      "cmd": "python3 benchmark/seats/seat-matrix.py --self-test",
      "exit_code": 0,
      "timeout_sec": 120
    },
    {
      "cmd": "python3 benchmark/probes/scripts/violation-rate-matrix.py --self-test",
      "exit_code": 0,
      "timeout_sec": 120
    },
    {
      "cmd": "bash benchmark/seats/recert-seats.sh --engines not-a-model --run-prefix specsmoke --skip violation,compliance,judge_quality,seat_matrix",
      "exit_code": 1,
      "timeout_sec": 120
    },
    {
      "cmd": "bash benchmark/seats/recert-seats.sh --engines claude-opus-4-8,claude-opus-5,codex --run-prefix specsmoke2 --skip violation,compliance,judge_quality,seat_matrix",
      "exit_code": 0,
      "timeout_sec": 120
    },
    {
      "cmd": "git check-ignore -q benchmark/seats/results/specsmoke2/recert-status.json",
      "exit_code": 0,
      "timeout_sec": 30
    }
  ]
}
```
