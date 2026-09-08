# Bind Codex judge measurements to the model actually invoked

## Goal and observed defect

The user requires trustworthy model/version replacement and role selection, with accuracy and complete intent first, verified-resolution speed second and OUTPUT/cost third. Existing judge-quality runs label `CODEX_MODEL`/`OPENAI_MODEL` as identity while omitting native `-m`; the regression test accepts this, and seat-matrix can replace missing identity with a declared run prefix. Such a result cannot justify changing a customer's model.

## Required behavior

1. Resolve the existing Codex model request once (`CODEX_MODEL` before `OPENAI_MODEL`) and pass it as an actual distinct model argument on every attempt. With no request, preserve native default selection and record the native observation. No new model/router/config surface.
2. Retain exact attempted argv, existing raw stdout/stderr, exits and native header observations for each attempt. Require a unique first native header before the echoed prompt, matching requested model when supplied, current cwd/read-only sandbox/xhigh effort and nonempty session. Missing, conflicting, spoofed-after-prompt or mismatched evidence is explicit identity failure and never a parse-error retry. Header evidence describes the native CLI, not independent provider internals.
3. Finalize observed run identity only when every associated attempt is bound to consistent native model evidence. Preserve unsuccessful and parse-rejected attempts; do not choose a convenient last header or erase errors. Native/transport failure cannot certify a run.
4. Reuse existing `judge-role-evidence.py` header parsing. Its production `describe` path must still require actual isolated wrapper and600-second markers. Extract only the native-parser portion; the direct benchmark retains its existing300-second bound. Never fabricate markers or pipeline state.
5. Seat-matrix's Codex judge-quality rows require the evidence-qualified identity associated with all record/attempt artifacts before assigning current exact-model status or certification. Declared environment/prefix labels cannot replace absent/conflicting evidence. Preserve diagnostic metrics and historical declared identity as report-only context. Other engine/suite behavior is unchanged and gains no new certification claim.
6. Retain the existing case scorer, prompt, isolation flags, effort, time bounds and parse-only retry policy. Do not regenerate historical results/reports, change customer AGENTS.md/CLAUDE.md, role defaults or frozen previous experiments. Live validation, if separately registered, uses a fresh owned results destination.

## Scope

Existing judge-quality runner and fake-native route test; seat-matrix and its existing temporary-repository regression test; native header helper and normal mirrors only if extraction is needed; concise benchmark/checkup documentation where its identity claim changes. Research/spec/closure records belong under autoresearch/docs, never customer entry contracts.

## Verification fixed before implementation

- Fake-native actual argv establishes request precedence; no-request observation follows native default.
- Valid JSON cannot rescue wrong/missing/duplicate native model, spoofed post-prompt header, or wrong cwd/sandbox/effort. Identity failure retains artifacts and does not trigger parse retries.
- A first parse failure followed by success retains both attempts. Model drift between attempts and unsuccessful execution prevent certification.
- Seat consumer accepts an intact consistently observed record set; missing/mixed/legacy evidence, altered associated artifacts or a declared prefix cannot manufacture current status/certification. Other-engine behavior and original legacy bytes remain unchanged.
- Existing production helper tests continue rejecting missing isolation/600-second wrapper markers; full `bash scripts/lint-skills.sh` is required if canonical installed helper changes.
- Independent source review and actual Fable5.1/Grok4.6 advisory review of the resulting source. Root decides; no majority/consensus gate and no quality/speed/model-fitness inference from source agreement.

## Acceptance and next decision

Accept only the source/functional measurement repair after relevant regressions and source reviews pass. Then a separately bounded native check can test requested-versus-observed model delivery before any old/new role comparison. A fair replacement study still needs fixed tasks/configuration, repeat policy, quality-first judgment and disjoint confirmation. No default promotion or3.0.0 publication follows automatically.

Subtractive-first: remove the environment-as-observation assignment and the Codex judge prefix bypass; move existing wrapper checks without relaxing them; add only per-attempt binding needed to prevent the demonstrated false attribution. Principles: No guesswork, No workaround, No overengineering, Production ready.
