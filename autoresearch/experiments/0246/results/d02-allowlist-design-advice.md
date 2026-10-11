# 0246 d02 allowlist interpretation advice

Recommendation: retain the observed **PRODUCT_INCOMPLETE / COMPLETE** row with verified nonactivation and continue the unchanged registered sequence, subject to its ordinary independent integrity/protocol checks. This evidence does not establish a machinery fault requiring STOP. Do not rerun d02, revise its verdict, force activation, or change the remaining inputs. This is bounded interpretation advice, not a new design approval or registration.

Independent reviewer `/root/review_0242`, 2026-10-10 UTC. Read-only inspection of the actual caller, prompt/plan, stdout, candidate guide/helper, verdict and registration. No tests, models or authentication; only this report was written.

## What actually happened

The before-end observation matches stdout line 23 and its hash. The owner had read both the peer guide and helper source, explicitly identified their extra in-repository records as outside the allowed files, and chose a direct local commit. The final answer repeats that independent review was skipped for this reason. No peer launch/session is present; the retained policy is MATCH / NOT_ACTIVATED, with no gaps or violations. This is observed nonactivation, not an unrecorded peer whose usage should be reconstructed.

The raw result is 404.69662925001467 owner seconds, 632,441 input / 19,184 output, complete usage, public checks passed, direct local delivery passed, CLEAN teardown. Only bin/cli.js and tests/cli.test.js changed, with no scope violations. The product fails the submillisecond-order and offset-equivalence oracle rows; the other two rows pass. Do not confuse source_check_pass:false with a permission/scope violation: here the missing source correctness is the two timestamp requirements. Nonactivation is recorded separately and does not itself make the source incorrect. Nor does the observation prove that an activated peer would have fixed these failures.

## Three different contracts

1. The actual caller says “Only touch” the two named files; the run prompt says to change only its allowed paths. It specifically permits Git internal metadata needed for commits/worktrees, not arbitrary extra records. The installed defaults cannot expand that permission. The owner's conservative refusal is a defensible response to the text; it should not be relabeled protocol misconduct because another owner might choose a narrower source-only interpretation.
2. The evaluator measures product-source scope. The inherited locator takes Git's tracked/nonignored product view and excludes .devlyn; checks compare that snapshot with the allowed source paths. Thus ignored .devlyn records would not be delivered source changes or trigger this evaluator's source-allowlist test. That explains the machinery's behavior; it is not proof that the caller authorized every filesystem write the evaluator ignores. Git-ignore status is a version-control property, not permission.
3. Native sessions, model transcripts, public-test fixtures and local Git delivery necessarily create runtime state in home, temporary or Git locations. Reading “only touch” as a prohibition on every filesystem side effect everywhere would contradict the requested checks/commit and execution itself. However, necessary native/tool-managed state does not automatically authorize a candidate's deliberate additional directory in the source checkout. The precise boundary is unstated; the present text does not explicitly declare ignored in-repo records allowed.

The helper's fixed repository-local custody is therefore a real compatibility limitation under a strict repository-path interpretation, and a trigger for ambiguous-contract handling under the source-only interpretation. It is not evidence that the helper's lifetime fix failed: no helper was invoked and no custody disappeared. The guide explicitly says that if the peer cannot run, report that fact and continue solo checks. That is what happened.

## Why this does not invalidate the registered screen

The screen measures ordinary-request activation as well as product correctness and resources. Its frozen rule says no activation is not automatically a source failure, earns no peer-check credit, and that product failure is a measured outcome; only machinery/auth/identity/accounting faults stop the sequence. The observed row fits those rules exactly. A candidate failing to activate under a real task constraint is informative treatment behavior, even if it exposes an actionable API limitation. It is not made an apparatus defect merely because it prevents the intended mechanism on this attempt.

An apparatus STOP would require separate evidence such as changed/unbound instructions, an uncollectable actual model call, inconsistent gate enforcement, or a task setup that prevents the required product result from being evaluated. None follows from this record. The required source task and direct local delivery remained executable and were evaluated. The common strict request was not added selectively to disadvantage this arm; it remains the frozen request for the comparisons.

The interpretation cannot support a clean claim about a peer's counterexample-finding ability, because no peer ran. It can support reporting the candidate's failure to activate and the resulting source/cost observation, with the owner's stated reason. Preserve the existing adaptive/exposure caveat and per-engine decisions.

## Smallest prospective follow-up, if needed after closure

Do not patch this during the sequence. The frozen candidate is measurable and there is no ongoing lost usage, unsafe write or invalid evaluator that makes completion impossible. Let the registered remaining cells establish whether this is isolated or recurrent before choosing a changed version. Retain this row even if a later design addresses it.

If strict repository allowlists must be supported, the root issue is custody location, not insufficient exhortation to call the peer. A future helper can retain the same exclusive, helper-owned per-call record set in one durable application-state location outside the source checkout, with repository attribution and canonical returned paths. That can preserve the 0245 lifetime invariant while avoiding extra repository writes; it need not restore caller-owned --out, add export copies, bypass source checks or introduce a storage framework. The existing home/native evidence domain provides a concrete place to investigate, but its exact lifecycle and collector binding would need prospective verification before implementation is accepted.

Relocation is not authority to disregard a caller that explicitly forbids all auxiliary state. If that prohibition applies, decline the peer and continue only the allowed work. Likewise, placing peer logs inside .git is not justified by the current narrow exception for metadata required by commits/worktrees. Do not disguise application records as commit metadata.

If the intended study contract instead distinguishes deliverable source from allowed runtime records, any clarification must be common to all arms and separately registered for a future comparison. It changes the prompt/treatment conditions; it cannot be inserted now or used to reinterpret this result favorably. Stronger prose claiming “ignored means permitted” would be a workaround. These boundaries follow **No workaround**, **No guesswork**, **No overengineering** and **Production ready**.

## Exact inspected bindings

- Before-end observation: 9d0a77ecdf66ff1261aca31b5d2ce38d61f6a86fe34f137fde29737d5c7cca7c
- Actual harness/caller.json: a01bf0477754f2a3474dd28cd4d210ce5237241ac0f589ecbd08f647d29b27ed
- Actual prompt.txt: 18da7b5870bf5d71457a1f3bf80eeada84da722ec41ce357ee0607d11efb7b38
- Actual plan.json: dd5ab391eb9f29b64bfa153e3624b4fee1bf32cde82a0f11b1efb6af5953f1cf
- Actual run/stdout: 9acd89988b47e306c920c19965841177d15627c96ee120cd1866bd0a6f85e744
- d02 raw verdict: 4dd81587abbb27528ccc70a594d0e5cb6dd5a7a31aa8fd33a7fa499a600c7dc9
- 0245/peer.py: b51b8c9db0b0d6c1b95e0134e6e3b9f83f27d4b63f6fece79b8e852d3d49d095
- 0245/guides/P.md: fa782da81c1da4c310d6dd22d2e2c5e560a30e8b50b3642181b85246fa7757a0
- 0246/registration-v1.md: dd489ac8b05e973dacf413852664f814bde2da8e731ab3d6f8db2565e215f853
