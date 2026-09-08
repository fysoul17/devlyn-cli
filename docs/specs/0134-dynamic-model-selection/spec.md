# Honor configured models without obsolete source pins

## User requirement and observed boundaries

The user asked on2026-09-08 whether static model names prevent new releases or user-selected models from working. Codex role selection already reads project/per-run values and native model metadata; example/test strings are not execution defaults. Two actual production restrictions remain: `role-config.py` requires the Claude effort declaration even for a model-only request, and SURFACE_CLOSE's skill command overrides native user selection with `claude-sonnet-5`.

Root selects a bounded follow-up after0133 source advice closes. Remove these restrictions using existing settings and evidence paths. Do not add a registry, role, flag, API-auth dependency, model ranking or automatic promotion. Preserve historical experiments and customer AGENTS.md/CLAUDE.md.

## Required behavior

1. A Claude CLI judge's exact model-only profile passes the selected string as `--model` without requiring a version/model effort declaration. Keep native version provenance, adapter/channel eligibility, existing exact native-result model validation, errors and bound artifacts. Unsupported native model requests still fail; aliases remain outside the explicit exact-ID contract. A model-only profile makes no effort-selection promise.
2. Explicit effort remains separately validated; do not delete its guard or assume equal effort labels imply equal capabilities. Unknown requested effort support remains an actionable failure. This correction does not claim to solve dynamic effort discovery or organization-imposed effort caps.
3. SURFACE_CLOSE inherits the existing native Claude model configuration by omitting the hardcoded model argument. Record `model_requested=null` for this inherited route and obtain `model_effective` from its existing native JSON result at completion. Allow omission at this phase's spawn, reject an explicit empty value, and retain all other phases' model requirements. A caller that explicitly supplies an exact model still gets requested/observed mismatch rejection.
4. SURFACE_CLOSE completion must require its prescribed native JSON evidence even when no model was requested; omission cannot become PASS with unknown identity. Preserve Claude-only routing, one-shot budget, capture, verification, rollback and failure/skip boundaries. Do not silently apply worker profiles to this separate phase.
5. Update only the affected runtime instructions, role/status documentation, state checks and lint contracts. Remove the lint exception that requires the obsolete Sonnet execution literal. Keep legitimate example/test IDs and the remaining explicit-effort declaration clearly scoped.

## Verification fixed before implementation

Predict that a synthetic new exact Claude model and new CLI version with no effort currently fail solely at the declaration lookup; after correction, exact argv selection succeeds while native mismatches/errors still fail. With effort requested, the same unsupported pair must still fail. Reuse existing role/native-evidence tests; no paid model-availability probing.

Test inherited SURFACE_CLOSE spawn followed by valid native modelUsage, missing/malformed/ambiguous model evidence, omitted session-log capture, explicit matching/mismatching identity and explicit blank model. Verify existing scope/input/one-shot/rollback/archive checks and unchanged PLAN/Codex requirements. Run required full lint and mirror parity, with source review before acceptance. These are functional configuration changes; no quality/speed/default-fitness claim follows.

Official native behavior checked2026-09-08: [Claude model configuration](https://code.claude.com/docs/en/model-config) documents environment/settings selection, actual JSON `modelUsage`, model remapping and effort fallback. This supports separating selection, support and observation; it is not proof that arbitrary future models preserve task quality.

Subtractive-first: remove the unnecessary model-only support-table dependency and execution literal; use existing native configuration instead of another variable/config layer. The necessary addition is the completion guard exposed by allowing inherited selection. Principles: No overengineering, No workaround, No guesswork, Production ready.
