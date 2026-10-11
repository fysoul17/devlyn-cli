# 0246 status

2026-10-10T18:46:20.081642+00:00 — registration cross-model SHIP; input freeze written;
independent final binding audit42/42 PASS. d02-f23-codex-p completed
PRODUCT_INCOMPLETE/COMPLETE; d03Claude/A completed CHECKS_PASS/COMPLETE; integrity30/30 PASS and process note complete.
d04Codex/H completed PRODUCT_INCOMPLETE/COMPLETE; integrity31/31 PASS.
0246 is CLOSED at d05Claude/P STOP/COMPLETE; remaining five cells NOT RUN.
Do not resume this sequence or regrade d05. Machinery-only repair is being
validated separately in0247. Earlier d02/d04 product failures and nonactivation
remain valid measured negatives; their verdicts and all costs are unchanged.

0245 native and both independent gates PASS. Reuse historical0243d01Claude/S
once with its original PASS and costs. Preserve originald02STOP/PARTIAL and
unknown residual/lower costs separately. New nine-cell sequence starts at
new-version d02-f23-codex-p, then follows the remaining original fixed order.
No ordinary request asks for pair. This is an adaptive exposed-task diagnostic
screen; positive signal still requires fresh harder repeated confirmation.

Registration: registration-v1.md,
SHA256dd489ac8b05e973dacf413852664f814bde2da8e731ab3d6f8db2565e215f853.
Review: results/registration-review-v1.md, SHIP, no CRITICAL/HIGH/MEDIUM.
Freeze: results/freeze-measured-v1.json,
SHA256fd3dcf7415e580b9c6b243148e61f5e7745cdb44be562458aeb37f003f74adab,
109 execution inputs,328 selected artifacts. Runtime:
/Users/aipalm/.local/share/nx01/0246-live/runtime-measured.json.
Use unchanged0245/runner.py; do not overlap an owner with independent study
models/reviews/heavy tests. Machinery/auth/identity/accounting faults STOP;
product failures remain measured. All old verdicts/gates/costs remain intact.

Final binding audit: results/freeze-audit-v1.json, SHA256
68e5f97b3b13a1b40b439ed13637595245bc56dbfe8184322afb4eb8d7fe683d.
Native d02 runner session78441 ended exit0; d03 session67724 ended exit0; d04 session81024 ended exit0; d05 session85407 ended exit2; no native owner is running. No independent
study model/reviewer/heavy test overlapped the owner.

## First new-version observation

2026-10-10T18:58:37.517910+00:00 — d02 Codex/P:
404.69662925001467s,632441 input/19184 output, COMPLETE and no gaps;
identity/policy/Claude-accounting MATCH and CLEAN teardown. Public51tests PASS;
priority-rollback and single-warehouse-fefo PASS; submillisecond-order and
offset-equivalence FAIL. Source/product incomplete; exact local delivery PASS.
Peer activated=false, validation_completion=NOT_ACTIVATED: the owner explicitly
skipped helper review because it interpreted its record files as outside the
requested two-file allowlist. Keep that observed nonactivation separate from
source failure. No peer novelty credit and no source repair/regrade. The
before-end statement and prediction are in results/d02-allowlist-observation-before-end.json.
Original0243d02STOP and old costs remain independent, unchanged evidence.

2026-10-10T19:04:00Z — d02 integrity27/27 PASS; report
results/d02-integrity-audit.json SHA256
d9d54a008373bca3e8ed0d298f397dbcbdf656877d039a5cb373703b0f40db31.
Allowlist advice results/d02-allowlist-design-advice.md SHA256
d5321d6c22614df9165cddb869bc40b9d09aee0a4e9783fb2c7f944d217e22bf.
Both agents idle before d03 dispatch; no conditions were changed or rerolled.

2026-10-10T19:17:57.384188+00:00 — d03Claude/A native CHECKS_PASS/COMPLETE:
825.7604531670222s,3441785 input/93953 output. All four oracle rows, public9,
source/product/exact local delivery PASS, no usage gaps, identity/policy/Claude
accounting MATCH and CLEAN teardown. Independent integrity and bounded process
checks are pending before d04. No inference or causal admission follows from
a single adaptive diagnostic observation.

2026-10-10T19:21:58.571441+00:00 — d03 independent integrity30/30 PASS:
results/d03-integrity-audit.json SHA256
3b6ffe91470230862379e35e6f3e8c356817adaab53f41f73e65c84f27017816.
Bounded results/d03-process-note.md SHA256
4b3781b186bbc7b086642f3d335e0c2ec4020bdfb363fbc864170b3ecbcba77e
qualifies mutation-batch totals and baseline directory-failure provenance; no
verdict/cost change. Both reviewers idle before unchanged d04Codex/H dispatch.

2026-10-10T19:29:30.875728+00:00 — d04Codex/H measured
PRODUCT_INCOMPLETE/COMPLETE:429.060545040993s,558535 input/20603 output. Public65
and exact local delivery PASS; submillisecond-order and offset-equivalence FAIL,
other two oracle rows PASS. Identity/policy/Claude-accounting MATCH, no gaps and
CLEAN teardown. No peer/children; owner explicitly skipped review because its
repo-local records exceed the caller's two-file allowance. Preserve this repeated
nonactivation separately from the product failures. Independent integrity pending
before d05Claude/P; no machinery STOP or midsequence input change.

2026-10-10T19:31:25.524994+00:00 — d04 integrity31/31 PASS;
results/d04-integrity-audit.json SHA256
1d62c6975225dc5ab0942b6cc33e0b1455e3bcc3fb511e5b2e1528078d6a779e.
Independent auditor idle before unchanged d05Claude/P dispatch. No repair/regrade
and no extra model/review/heavy-test overlap.

2026-10-10T20:11:38.716398+00:00 — CLOSED at d05Claude/P STOP/COMPLETE:
2138.6585267500195s,12316264 input/196529 output, no gaps, identity/policy/Claude
accounting MATCH and CLEAN teardown. Exact emitted STOP reason is
`ValueError: Claude startup catalog missing or ambiguous`: two actual system/init
rows have the same native session/model/catalogs. The frozen extractor requires
exactly one. Separately, the Codex peer's valid56 LF-delimited JSONL records
contain a literal U+2028; peer.py str.splitlines produces57 fragments and reports
NATIVE_FAILED despite native exit0 and stable source. Peer policy is activated
true / INCOMPLETE, not recovered. Original source/public/oracle/delivery gates
remain NOT_GRADED_AFTER_STOP. Owner-consumed answer, repairs and local commit
are separate process observations, not a regrade or admitted efficacy result.

Independent integrity30/30 PASS; report SHA256
a4a289e94c6ef75500a279fb10ec63423af4ef18d3bac13873952e917ccba0a4.
Two Claude segments reconcile to11960264 input/185442 output; native Codex peer
356000 input/11087 output, summed once to the original complete total. Container
and temporary volume absent. Preserve every earlier0243/0245/0246 result and
cost. d06Codex/B, d07Claude/H, d08Codex/A, d09Claude/B, d10Codex/S remain NOT RUN.
Native protocol audit and bounded prospective design advice are pending.

2026-10-10T20:22:27.350459+00:00 — Native protocol audit and bounded design advice are complete.
results/d05-native-jsonl-audit.md SHA256
ec3891c92458501868b6be04d1a0ab284ca6844a2feb177059ac99a0565cb265;
results/d05-jsonl-design-advice.md SHA256
a29a4f6d35a547d005229dcb9967cda0612c3fcad9165bdb1faf841c50a9a4c7.
Both distinct machinery failures are reproduced without regrading the cell.
0247 validates LF record framing and consistent repeated startup catalogs only.
Repo-local custody/activation remain unchanged; external custody is a separate
proposal, not bundled into the remaining comparable question. No native owner
is running at this checkpoint.
