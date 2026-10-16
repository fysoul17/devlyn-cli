1. **HIGH — Claude bearer tokens can enter sealed evidence.** [runner.py:32](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d4/autoresearch/experiments/rp-d4-helper-report/runner.py:32) reuses the Codex scanner, which scans the PAT and `codex.json` tokens but never the guard’s `CLAUDE_CODE_OAUTH_TOKEN`. A guard printing its environment can therefore leak its bearer into retained evidence. An in-memory probe reached the inherited seal with that synthetic token present.
   
   **Fix:** scan the selected Claude bearer before sealing and during final archive/record scans, preserving STOP/revocation behavior. Add a Claude-token leak test; the existing guard test covers only its bundled Codex token.

2. **HIGH — Ordinary helper invocation syntax can hide `merge_refused`.** [smoke.py:397](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d4/autoresearch/experiments/rp-d4-helper-report/smoke.py:397) discards outputs when its command parser does not recognize the launch. For `helper=/path/task-complete.py; python3 "$helper" complete --receipt …`, a valid refusal is ignored. A refusal followed by a literal successful invocation produces `merge_refused=False`, permitting adoption despite DESIGN’s mandatory INCONCLUSIVE rule.
   
   **Fix:** bind structured results to the current receipt while preserving continuation provenance; ambiguous execution evidence must fail closed. Add variable-path/wrapper and refusal-then-success regressions. Summary tests that inject the boolean do not cover this producer failure.

3. **MEDIUM — Spare-smoke consumption is confined to one stage directory.** [stage.py:43](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d4/autoresearch/experiments/rp-d4-helper-report/stage.py:43) accepts a fresh spare stage without binding it to the initial attempt. [runner.py:144](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d4/autoresearch/experiments/rp-d4-helper-report/runner.py:144) checks no predecessor for `smoke2-codex-X`—confirmed by a probe recording zero reads. The README’s fresh-directory workflow therefore allows another spare after STOP and does not enforce unchanged accounts/arms across attempts.
   
   **Fix:** retain shared run-level consumption/STOP state and bind the spare to its failed predecessor and frozen inputs. Test cross-directory replay and input/account drift.

Otherwise, inspected arm/install bindings, observer isolation, schedule, renewal boundaries, and summary branches—including FALSE, guards, dominance and strict improvement—match the contract.

Validation: **16 tests and 12 subtests passed** without temporary files. The documented full suite could not start because the read-only sandbox provides no writable temporary directory. No files changed or live runs performed.

VERDICT: REVISE
