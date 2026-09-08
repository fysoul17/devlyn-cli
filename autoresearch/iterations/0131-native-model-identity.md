# 0131 — Trustworthy Codex judge model identity

Status: SPECIFIED BEFORE IMPLEMENTATION; no native comparison or promotion.

The next model-selection decision is unsafe while the benchmark records an environment label without dispatching it. Source audit found no `-m` in `run_judge_quality.py`'s Codex route while `write_identity` records CODEX_MODEL/OPENAI_MODEL. The fake-route regression repeats the assumption, and seat-matrix's prefix attestation can replace identity with declared versions. The violated invariant is requested model → actual argv → observed native identity → associated scored rows. The [spec](../../docs/specs/0131-native-model-identity/spec.md) owns the bounded repair and pre-implementation checks; proposal `.devlyn/0131-model-identity-preparation-r0/PROPOSAL.md` SHA b0ab4d03dd90efa7ec068c40857e914833495c57c436c863b3013670ed110e92 records the source audit.

Prediction: matching native evidence can label the observed model; missing, mismatched or unassociated evidence cannot certify Codex judge results even with perfect diagnostic scores or an attested run prefix. Existing production wrapper checks remain required. Falsifiers are a fake-native mismatch accepted as current/certified, a lost prior attempt, or weakened production isolation/time-bound verification.

This repairs a concrete measurement bug before a model replacement decision; it adds no evaluation platform or routing policy. Preserve historical results,0124/0125/0128 closure and A16 parking. Customer role controls/defaults and3.0.0 publication remain unchanged. Existing shared parsing and regression tools are reused. Actual Fable5.1/Grok4.6 source advice is advisory; root owns acceptance. No native accuracy/speed/OUTPUT benefit is presumed.
