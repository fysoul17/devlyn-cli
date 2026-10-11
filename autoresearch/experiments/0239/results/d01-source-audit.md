# d01 Claude C: final source audit

**No supported source blocker found in this bounded audit.** The final implementation supports the requested reload, include, merge, publication and public isolation behavior. The oracle's single-read/same-call-byte gap is supported by the source path described below, not retroactively counted as an extra oracle pass. This is an audit of one finalized exposed development cell, not a candidate-admission decision or evidence of a bare-model gain.

Artifact root: `/Users/aipalm/.local/share/nx01/0239-live/staged-v1/out-development/d01-claude-c/`. `S` below means `snapshot/visible/`; native event references are physical lines in `run/stdout`. Public obligations are the unchanged `0239/fixtures/CFG-LIFE/goal.md`, `visible/docs/format.md` and `visible/docs/reload.md`.

No source edits, new execution probes, suites, model/Docker/auth calls, or other cells were used. The existing native reviewer terminal notification at line2824 was read first, then the owner fixes and retained post-fix results. A separate read-only subagent checked preservation, APIs and commit/artifact binding.

## Final source versus the public contract

| Contract | Final source evidence |
| --- | --- |
| Read each canonical document at most once per load; shared includes see the same bytes | `S/beacon/loader.py:10–11` creates `resolved` and `active` inside each `load`. A new resolver performs the sole `read_document` at line22; lines26–30 reject an active cycle and schedule only a child absent from `resolved`. Completed results are cached at line31 and reused for later branches. `document.py:6` reads the document once. Local parsed data is held while children resolve; `merge.py:5–14` copies rather than mutates the cached layers. Thus a later branch reuses the same already-read values even if the file changes externally after that read. No instance/global cache survives into a later load. |
| Ordered includes, recursive objects, replacement for other value kinds; legal diamonds and canonical cycles | `loader.py:24–31` gathers include results in list order and applies local values last. `merge.py:6–14` finishes each layer before the next, recursively merging only two dictionaries via an explicit stack; other values replace. `loader.py:25–27` canonicalizes relative to the declaring file and checks the current active stack. Completed paths are reusable. |
| Complete current dependencies and freshness | `loader.py:44` returns sorted canonical `Path` keys from this call's completed graph, including root. `paths.py:4–10` resolves paths with `realpath`; no file metadata determines cache reuse. Failed partial graphs cannot persist into another invocation. |
| Failed reload preserves state and repair recovers | `manager.py:38` completes loading before reading/updating publication state; assignment occurs only at line46. A loader error leaves `_current` unchanged. Per-call loader state makes a repaired graph retryable. `document.py:5–16` converts documented read/JSON/schema failures to `ConfigError`; include/root diagnostics use the exported path/chain fields. |
| Generations and refreshed dependencies | `manager.py:40–46` starts at1, preserves generation for equal effective values, increments on differences, and publishes the new dependency tuple even when generation stays equal. `_same` compares nested dictionaries/lists structurally without depending on key order. Its numeric interpretation is disclosed below. |
| Detached public results | `model.py:15–27` iteratively copies JSON dictionaries/lists. `manager.py:35,46–47` copies stored values on input and every public `current`/reload return, with immutable dependency tuples. Loader results have no state reachable by a later invocation; merged layers are copied. This conclusion does not require an unrequested private-helper ownership rule. |

The participant also added `checks/test_includes.py:60–67`, wrapping its actual `read_document` call to verify one call per document and a fresh set on the next load. That is evidence about this implementation and test suite, not a replacement universal oracle or a new restriction on equivalent I/O primitives. The retained post-fix mutation output at line3095 reports its no-per-load-memo mutant was caught. No new race experiment was run here.

## Reviewer findings and subsequent changes

The native reviewer completed at line2824 with nothing above LOW, reporting broad differential fuzz on Python3.12.14. Its findings refer to an intermediate implementation and must not be reported as unresolved final defects:

- At line2980 the owner replaced JSON serialization comparison with the final explicit-stack `_same` and converted published dependencies to a tuple. This addresses the witnessed deep-comparison exception and dependency-list sharing. Post-fix retained probe output at line3027 shows the previous deep-callback case recovering, custom-loader comparison cases succeeding, and dependency-list mutation no longer leaking.
- At line2982 the owner changed `locate` to forward only the actual arguments, restoring the root's one-argument `canonical` call. Line3027 confirms that root stand-in case succeeds.
- `merge(base, override, *later)` remains variadic and the loader uses additional layers. Direct two-argument calls still work; a patched strict two-argument stand-in inside `beacon.loader` no longer does. The visible exported API list does not promise this internal monkeypatch call shape, so this is a disclosed compatibility detail, not a supported exported-API blocker.
- Line3124 retains post-fix checks (`37 tests … OK`), symptom probes and fuzz results. Its initial `FAILED (failures=1)` is explicitly the deliberately broken key-order mutant, followed by the unmodified-source checks passing; it is not a final product test failure. The broader mutation/fuzz claims were not independently reproduced or regraded here.

## Preservation and delivery integrity

- All four original QA files are byte-identical: `checks/helpers.py`, `run_checks.py`, `test_format.py`, `test_smoke.py` (five original test methods). The three new modules add 16 include, 5 merge and 11 reload methods: 32 added, 37 total. Original QA was not weakened.
- README and all three visible docs (`format`, `incident`, `reload`) are byte-identical. Exactly six implementation files changed and three test files were added; original visible files19, final visible files22.
- `beacon/__init__.py`/`__all__` and `ConfigError` are byte-identical. `Resolved` and `Snapshot` class ASTs, frozen decorators and fields are unchanged. Public `Loader.load`, `ConfigManager.__init__(path, loader=None)`, `current`, and `reload` signatures remain. Removing the old private `_cache` and explicit no-argument `Loader.__init__` preserves normal `Loader()` construction.
- All70 snapshot files match content and Git modes in local commit `635ae29d07aadec822122a7a852b0f2a78f4dc93`, parent `c1c21800d26bd174a2c27fe057f11ed66724a83f`, with no omissions/extras. The nine changed paths exactly match `delivery.json` and verdict. All896 evidence-manifest file hashes match, and its own hash matches the verdict. Root's separately retained `d01-commit-binding-v2.json` uses raw `ls-tree`/`cat-file` for the same binding, avoiding archive-output mode transformations.
- The retained verdict says `CHECKS_PASS`: public37 pass, oracle12/12, source/delivery true, usage COMPLETE, identity MATCH, teardown CLEAN. These existing observations were not rerun. Recorded cost is 3477.738696790999 owner seconds, 25,986,453 input and 411,981 output tokens. **Native aggregate-versus-terminal usage reconciliation remains a separate open audit** (root reports a 141,087-input/5-output discrepancy under investigation). This source report does not independently certify the COMPLETE accounting label, resolve that discrepancy, or authorize d02.

## Boundaries and hashes

The final implementation deliberately distinguishes `1` from `1.0` for generation changes (`manager.py:6,10–11`), and explicitly reports that interpretation at native line3314. The unchanged contract does not settle that numeric-equivalence choice precisely enough to introduce a new binary failure here. The final code treats equal signed floating zero as equal; the review's earlier serialization-based signed-zero observation is superseded (line3027).

The parser still accepts NaN/Infinity as before (`document.py:6`); this pre-existing permissiveness was disclosed by reviewer and owner and is not silently promoted to a new strict experimental oracle. Nor are private helper result ownership, arbitrary non-JSON loader values, extreme platform limits, or internal stand-in signatures turned into new task requirements. The source analysis above applies to documented JSON values and the observed Python3.12.14/Linux path; it does not establish every cross-platform edge, concurrent `ConfigManager.reload` semantics, or an exhaustive proof of all inputs.

SHA256 bindings:

| Artifact | SHA256 |
| --- | --- |
| Sibling `verdict-d01-claude-c.json` | `248f0764d9f35ecc2ce78df329c7fa4300f08128ab6a61314335d51c269de488` |
| `run/stdout` | `03595a45cef6fafd3727a5223d42c336fc289834640c8373d955046b50e5b2d7` |
| `evidence.manifest.json` | `60b835ad96ebd995a98125d464defa9dc2885f62650a1e351da719bd1bdc8c4a` |
| `delivery.json` | `d175ddeec0a4e35d9b87d15316d0b63eab34bcc9f59cd9f0080174653a3e4e68` |
| `S/beacon/loader.py` | `de3e3e74b96babd0efa2fc33efab715b5bc9ef1f483c2fbddee28140551e640b` |
| `S/beacon/manager.py` | `ac0755381349961379c22ae7a27fdb8d5f979eb41528696901e3a799387f432c` |
