# 0241 implementation review v1

Verdict: FINDINGS — one MEDIUM; correct before native validation. No CRITICAL or HIGH finding. This is an implementation review, not an efficacy/adoption verdict or dispatch authorization.

Reviewed manifest: `results/review-manifest-v1.json`, SHA-256 `8760a3f41f6854e372ce6d37eea81070651c03767b7110778e636cc7d58b72a7`. Read-only hash verification found zero mismatches across its 38 files and four explicitly bound dependencies. Review considered DESIGN, the new implementation, inherited identity/policy/accounting/source/delivery gates, fixture source, `implementation-v1.json`, retained test log and component replay. No tests, model/native/auth calls or old-cell writes were performed by this reviewer.

## MEDIUM: literal home captures use the wrong retained mount

Location: `capture_discovery.py:69-82`.

`redirected_paths()` maps `/home` to `out/home`, while the actual native runner mounts `out/home` at `/home/participant` (`../0234/cell.py:140`; the existing source locator agrees at `../0234/locate.py:17`). Consequently, the supported literal command `claude -p --output-format json prompt > /home/participant/capture.json` produces retained `out/home/capture.json`, but discovery expects nonexistent `out/home/participant/capture.json`. Its suffix matching also uses the untranslated `home/participant/capture.json`, so it cannot find the real carrier. Content discovery may independently find the valid envelope, but the invented missing expected path remains unreadable and causes an otherwise fully accounted run to STOP.

This is a new false accounting gap on a real writable mount, contrary to **No workaround**, **No guesswork** and **Production ready**. It is fail-closed rather than an undercount/security bypass, and the guide's receipt-based helper route is unaffected.

Minimal correction: use the actual `/home/participant` mount and consistently use the translated retained-relative path when resolving absolute-path materialized/custody copies. Preserve unsupported-mount rejection and resolved-path containment. Do not merely change the prefix while leaving custody suffix matching untranslated.

Proposed check (not executed): create a valid Claude envelope at `out/home/capture.json`, add a native launch with stdout redirected to `/home/participant/capture.json`, and require the same discovered session with no unreadable carrier. Check its retained custody copy, missing/corrupt primary and custody cases, and an unsupported `/home/other` path. A focused fixture should distinguish correct native mount translation from acceptance based only on envelope content.

## Other conclusions

- `peer.py` differs from 0240 only by literal `features.multi_agent=false` to `agents.enabled=false`; both fresh and resumed Codex peers inherit it. Owner preparation/capability and Claude peer argv remain unchanged. Actual fresh/resume native tool catalogs must still prove capability removal; argument presence or no observed child is insufficient.
- Expected captures derive from typed Claude receipts, legacy dispatch records and bounded literal native launch redirects. Ordinary witness filenames no longer create work. Content-based unregistered result discovery remains, and missing/malformed/sessionless/usage-less declared captures continue into explicit gaps through the shared evidence object.
- `runner.py` binds that object to both identity and usage and leaves inherited peer policy, Claude terminal reconciliation, genuine interrupted-inference handling, source selection, delivery and STOP decisions in place. Native owner children remain allowed; peer-child protocol violations retain their costs.
- The retained test log reports 37 passing tests; this reviewer did not rerun them. The retained replay removes the four duplicated ordinary witness unreadable entries, preserves actual Claude envelope/totals, and retains the interrupted Codex inference gap. It is component diagnosis only. Prior 0238/0240 STOP/PARTIAL results and 0240's failed tool-capability gate remain valid historical outcomes.

After the narrow mount correction and targeted verification, rebind the changed bytes for a focused final review. Native validation remains a separate prospective, registered step; no performance or adoption claim follows from these changes.
