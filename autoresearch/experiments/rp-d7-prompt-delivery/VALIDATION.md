# Offline validation

Run the four-directory loop in [README.md](README.md#offline-checks). It adds
rp-d7 to rp-d6's existing PYTHONPATH and runs rp-d7, rp-d6, rp-d4 and rp-d5
separately, with pytest plugins, bytecode and cache writes disabled.

The rp-d7 suite uses synthetic archives, credentials and sealed evidence.
Sockets, URL access and subprocess launches fail immediately in its fixtures;
fake lifecycle methods never dispatch an experiment. Inherited suites retain
their local Git tests and mocked service/CLI responses.

| Tests | Coverage |
|---|---|
| `test_pack.py` | Registry X bytes retained exactly; SHA-256 and SHA-512 checked independently; X-only provenance; rejected Y, altered metadata, manifest and archive bytes. |
| `test_runtime.py` | Exact P1 source/result hashes, replacements, newline and length; mutation of body, argv, caller, plan/baseline hashes, release and arm; installed managed blocks/runtime principles and cache; four Claude high slots; exact repository names; one smoke and one spare; registry binding; non-delivering smoke qualification; failed smoke gates; source-cache drift; stop without replacement; slot pause/resume; renewal after odd/even completed slots and rejection mid-slot/after STOP/account change; 6300-second floor; all-request effort scan and structure-free merge refusal scan. |
| `test_grading.py` | Quality/skip/other precedence; skip candidates; every unknown count path including boolean/noninteger values; independent bound reviews; history citations from both reviewers; seal/parse/census constraints; command witnesses; no contradiction of positive observations; recomputed false completion after no-push review; substring quotes; allowed tags, agreement, disagreement and unset tags/report; unchanged inherited mechanical assessment. |
| `test_summary.py` | Every ordered decision branch, INCONCLUSIVE before UNSAFE, UNSAFE before outcomes; routing (a) before (b) before (c) before (d); both prediction clauses; failed-slot cost inclusion, missing cost and zero-delivery denominators; calculated exact Fisher tails; actual rp-d6 X reference; templates, persisted adjudication, provisional summaries and tag disagreement; evidence mutation rejection; incomplete schedule; JSON/Markdown output outside retained evidence. |

The inherited rp-d6/rp-d4/rp-d5 suites cover the reused Git-mode scope and
sentinel preservation grading, exact merged-PR proof, usage accounting,
credential scans, seals, archive custody, deletion/404, model identities,
effort and smoke/renewal machinery. They also verify that rp-d7's private
module adaptation does not change the original apparatus contracts.

This is apparatus validation, not a live result: no smoke or measured cell,
GitHub request, model API request, image build or commit is part of these checks.
