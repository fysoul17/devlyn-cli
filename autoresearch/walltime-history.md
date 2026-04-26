# Wall-time + work-product history — F4/F5/F6 across iterations

**Status**: Read-only diagnostic appendix to iter-0007 F6 isolation. **No decision authority** unless step-change correlates with iter-0006.

Built per Codex round 15 guidance (fold iter-0008 wall-time into iter-0007). **Round 16 caught two corrections to my first draft of this doc — both incorporated below.**

## F6-dep-audit-native-module — variant arm output across iterations

| Run | Iter | wall | timed_out | invoke_exit | **files** | diff_bytes | verify | bare wall |
|---|---|---|---|---|---|---|---|---|
| 20260423T134208Z | v3.6-ab baseline | 1966s | True | 0 | 2 | 4638 | 0.83 | 65s |
| 20260424T070557Z | iter-0001 v3.7-skillfix | 1159s | False | 0 | **4** | 5906 | 0.83 | 76s |
| 20260424T134305Z | iter-0001 v3.7-final | 297s | False | 0 | **3** | 4459 | 0.83 | 57s |
| 20260424T234714Z | iter-0002 v3.7-fix-f6f7 | 1400s | False | 0 | **3** | 4483 | 0.83 | 52s |
| 20260425T125125Z | iter-0005-full | 1496s | False | 124 | 2 | 4016 | 0.83 | 65s |
| **20260426T034926Z** | **iter-0006-full** | **1762s** | **True** | **124** | **0** | **0** | **0.33** | **59s** |

**Correction (Round 16)**: my first draft of this doc claimed iter-0001/0002 F6 variant runs had 0 files — that was a CSV-column misread on my part (I read `invoke_exit=0` as `files=0`). Actual values are 4, 3, 3 files with non-empty diffs. Codex Round 16 caught this directly from result.json.

**Implication of corrected data**: F6's variant arm produced consistent work (2-4 files, 4-6KB diff, verify 0.83) across **every prior iteration**. **iter-0006-full F6 is the first run in measurement history with 0 files / 0 bytes / verify 0.33 / timed_out=true.** This is a clean break, not chronic noise.

Verify 0.83 baseline is an artifact of a harness false-negative: `node --test` emits TAP `# fail 0` which trips the fixture's `stdout_not_contains: "fail "` rule, capping verify at 5/6 (~0.83). The chronic 0.83 represents working implementation, not partial work. iter-0006-full's 0.33 = 2/6 ≈ implementation absent.

**Implication for iter-0007**: Run 2 (d895ffa F6 alone) is now the load-bearing experiment. If d895ffa's variant produces ≥2 files / ≥3KB diff / verify ≥0.66 (matching the chronic baseline), the iter-0006 contract is directly implicated in the F6 collapse → REVERT.

**The "chronic slowness" sub-finding stands**: F6 variant has been 5-30× slower than bare across every iter. That's a separate latent harness-quality concern but not iter-0006-caused. Queue post-iter-0007.

## F4-web-browser-design — full-suite-only collapse on iter-0006-full

| Run | Iter | variant wall | bare wall | variant verify | bare verify |
|---|---|---|---|---|---|
| 20260423T134208Z | v3.6-ab | 840s | 419s | 1.0 | 0.75 |
| 20260424T134305Z | iter-0001 v3.7-final | 835s | 236s | 1.0 | 0.75 |
| 20260425T125125Z | iter-0005-full | 924s | 188s | 1.0 | 0.75 |
| 20260426T011548Z | iter-0006-f4 single | 688s | 171s | 1.0 | 0.75 |
| **20260426T034926Z** | **iter-0006-full** | **1038s** | **6351s** | **0.0** | **0.0** |

F4 was healthy (verify 1.0/0.75) in every prior iter **including iter-0006 single-fixture**. iter-0006-full is the only run where **both arms simultaneously collapsed** to verify 0.0 with bare hitting 6351s wall.

**Mechanism — Round 16 sharpening**: Codex Round 16 inspected per-arm artifacts directly and found explicit API transport failures: `Stream idle timeout`, `FailedToOpenSocket`, `ConnectionRefused`. The collapse is **shared runtime / API failure**, not "generic environmental noise" (my first-draft phrasing was too vague). A skill-contract change in `config/skills/_shared/codex-config.md` cannot mechanism-determinately cause both arms to fail — variant and bare get fresh `/tmp/bench-...` workspaces, and only variant copies the iter-0006 skill changes. The shared channels (`HOME`, plugins/hooks, API/network state, suite-resource-exhaustion) are the credible explanation.

## F5-fix-loop-red-green — same signature as F4

| Run | Iter | variant wall | bare wall | variant files | variant verify |
|---|---|---|---|---|---|
| 20260423T134208Z | v3.6-ab | 659s | 45s | 1 | 0.8 |
| 20260424T134305Z | iter-0001 v3.7-final | 973s | 40s | 1 | 0.8 |
| 20260425T125125Z | iter-0005-full | 1501s | 41s | 0 | 0.4 (timed out) |
| 20260426T005514Z | iter-0006-f5 single | 1133s | 37s | 1 | 0.8 |
| **20260426T034926Z** | **iter-0006-full** | **5630s** | **4611s** | **0** | **0.4** |

iter-0006 single-fixture F5 was healthy (1133s, 1 file, verify 0.8). iter-0006-full caused both-arm collapse (5630s/4611s walls, 0 files, verify 0.4 each). Same shared-runtime-failure signature as F4.

## Conclusion

**iter-0008 (separate wall-time investigation iteration) is unnecessary.** Per Round 16's clarification:

1. **F4/F5 collapse** = shared-runtime/API-transport failure during the 7hr suite. No iter-0006-mechanism is consistent with both-arm collapse on isolated workspaces.
2. **F6 chronic slowness** = pre-existing harness latent issue (5-30× variant/bare wall delta) that has been present since v3.6-ab but not impactful on score. Queue as post-iter-0007 candidate, not as iter-0008.
3. **F6 work-product collapse in iter-0006-full** = NEW. Genuinely unique to iter-0006-full. **The load-bearing question for iter-0006 ship-fate.**

**For iter-0007 Run 2 (d895ffa F6 alone)** — additional diagnostics to capture per Codex Round 16:

- `transcript.txt` byte count + first error line
- `claude-debug.log` API-error counts (grep for `Stream idle timeout`, `FailedToOpenSocket`, `ConnectionRefused`)
- `.devlyn/pipeline.state.json` phase keys + `phases.build.agent` value
- `git log` after scaffold initialization
- `changed-files.txt` and `diff.patch` size
- verify command failure tails

**Decision rule (sharpened from Round 16)**:

- If d895ffa F6 also has zero transcript / empty diff / no pipeline phases / API errors → F6 collapse is shared-runtime noise, NOT contract-caused. Contract stays. F6 becomes its own iter on the chronic-slowness axis.
- If d895ffa F6 enters BUILD and produces ≥1 file (matching the chronic baseline) while iter-0006 F6 does not → contract is **directly implicated** → REVERT iter-0006 commit.

The decision rule no longer leans solely on the ≥20-score-regression heuristic; it leans on **whether the BUILD pipeline ran at all on each side**.
