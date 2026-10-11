# 0247 prospective machinery repair — prediction and scope v1

Written 2026-10-10T20:14:19.499051+00:00 before implementation or new experiments. No native dispatch is authorized by this design file; a reviewed operational registration and final input freeze remain required.

0246 is closed at d05 STOP/COMPLETE. Preserve its exact startup-catalog STOP, separate peer NATIVE_FAILED, all ungraded post-STOP outcomes, full12316264 input/196529 output and2138.6585267500195 owner seconds. The five remaining cells stay unrun under0246. Independent integrity30/30 and native protocol audit pass as audits of preserved evidence, not product acceptance.

## Observed invariants

1. Native JSONL records are LF-delimited. Literal U+2028 in a JSON string is payload. The exact d05 peer capture has56 valid LF records; str.splitlines creates57 pieces. The helper rejects the valid answer, and the shared evidence inventory loses the affected command event. The helper must still strictly reject genuinely malformed JSON and failed/missing/duplicate terminal success. Inventory tolerance and accounting/gap rules are otherwise unchanged.
2. A native owner can emit repeated system/init records during one retained execution. In d05, the second follows its background peer completion notification. Both records bind the same session/model/tools/skills/plugins/MCP catalogs; only cwd/uuid differ. The invariant is consistent observed owner identity and the frozen startup catalogs, not exactly one notification. Require at least one well-formed init and validate EVERY init; reject missing/empty identities, conflicting sessions/models and conflicting/malformed catalogs. Do not pick a favorable first/last row. Existing actual-native identity and runtime expected-catalog comparison remain authoritative and unchanged.

## Smallest implementation

- New peer.py copies0245 exactly except its Codex JSONL split uses LF. Keep canonical repo-local custody, API, argv, prompt/answer, source stability and lifetime semantics unchanged.
- New runner binds an LF-framed inventory reader to the actual shared evidence inventory and cell-stream entry, retaining their current dict-only/tolerant-row behavior. No old module file is edited. Bind a new copy of0244 inline-result discovery with its JSONL boundary using LF; preserve terminal-candidate and fail-closed capture logic.
- Override only startup catalog extraction to validate all init identities and normalized explicit catalogs. Keep owner capabilities, model/effort identity checks, source/public/oracle/delivery gates, usage/accounting and all budgets unchanged. No extra collector namespace, parser framework or fallback success receipt.
- New package builder and copied guides must leave B/S archives byte-identical; H/P differ only in peer.py. No trigger, ordinary caller, guide wording or output storage change.

## Falsifiable prediction before tests

The retained Unicode command event and valid final answers containing U+2028/U+2029/NEL survive LF framing with exact payload and native bytes; LF/CRLF cases succeed. Genuine malformed JSON, failed/error turns, absent final answers and missing/duplicate success still reject. Inventory retains the exact formerly dropped event without altering valid terminal accounting. The retained consistent init pair yields the same explicit catalog as either member; absent/malformed catalogs and different/missing/empty owner session/model fail. Runtime expected-catalog mismatches still fail. Valid single-init behavior remains exact.

Targeted tests exercise these contrasts, installed/fake native helper behavior, and unchanged custody failures/resume/native argv. Tests must prove the new Runner actually binds both inventory and cell-stream paths and discovery, not merely test an unused helper. Preserve raw results, input hashes and old failing artifacts. A focused frozen Claude-owner/Codex-peer operational run follows reviewed tests/installations, with complete usage/custody/answer consumption/source/local delivery and independent audits. Exact regression witnesses are decisive even if a stochastic smoke does not emit both shapes; observed native shapes must be reported honestly.

## Treatment and inference boundary

This is machinery-only. Repeated strict-allowlist nonactivation in0246d02P/d04H is preserved as a valid negative for the same treatment; no retake buys another activation chance. External helper-owned home custody is an earned but separate activation-candidate proposal, deliberately not bundled here. After operational acceptance, a separately reviewed registration may resume only the unmeasured frontier and reuse exact relevant earlier A/S and valid inactive H/P observations once, with explicit exposure, applicability proof and complete old/new expenditure. No d05 repair/regrade; no positive selection of outcomes. Completing the registered no-signal decision closes this mechanism; a label/version change does not evade that rule. No native performance or product admission follows from machinery validation.

Principles: No workaround (actual delimiters and observed identity), No guesswork (predictions before experiments, preserved old verdicts), No overengineering (only bound readers and one guard), Production ready (unknown/malformed/conflicting evidence still fails).
