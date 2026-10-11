# 0241 targeted implementation review v2

Verdict: FINDINGS — the v1 MEDIUM is partially resolved; translated custody matching remains unresolved. No CRITICAL or HIGH finding. No SHIP-for-native-validation verdict for these exact bytes.

Manifest: `results/review-manifest-v2.json`, SHA-256 `c3589b85977749393738dd2b8351d42d3e6f2413bbffd71ee48bb8c00cfd2c38`. Read-only verification found zero mismatches across all 38 listed files and four explicitly bound dependencies. Comparing v1 and v2 manifests confirms only `capture_discovery.py` and `test_runner.py` changed. Review read the archived v1 sources, exact diff, `implementation-v2.json`, both home-mount prediction files and both retained test logs. No tests, native/model/auth calls or old-cell writes were performed by this reviewer.

## Resolved portions

The mount now correctly translates `/home/participant/capture.json` to `out/home/capture.json`. Absolute-path normalization rejects `/home/participant/../capture.json` as unsupported instead of treating it as a participant-home path. Canonicalizing the collector's `out` root resolves the macOS `/var` versus `/private/var` mismatch exposed in the first retained test run. Resolved-path containment continues to reject captures symlinked outside retained evidence.

The retained first run reports 39 successful tests and one root-alias error; the second reports 40/40 PASS. The three added fixtures verify existing/missing home capture, unsupported home paths and outside symlinks. They do not cover home custody copies.

## Remaining MEDIUM: absolute custody suffix is still untranslated

Location: `capture_discovery.py:80-86`.

The v1 review explicitly required translating both the mount and the custody suffix. The latter line remains unchanged:

```python
relative = str(primary.resolve().relative_to(out.resolve())) if '..' in path.parts else str(path).lstrip('/')
```

For normalized `/home/participant/capture.json`, `relative` is still `home/participant/capture.json`, although the retained path is `home/capture.json`. Therefore the copy search cannot recognize a retained `cell/work/.git/custody/home/capture.json`. If the primary was removed after custody preservation, discovery adds missing `home/capture.json` even when the valid custody carrier is present. If the primary is valid and that custody copy is corrupt, the corrupt copy is not classified as expected and its malformed contents are silently skipped by content discovery. Both contradict the function's promise to retain all materialized/custody copies and the existing malformed-custody control.

This is the unfinished portion of the original finding, not a request for a broader framework. Under **No workaround** and **Production ready**, use the translated retained-relative suffix for absolute captures while preserving existing relative-path custody behavior. Add the omitted regression with a home custody carrier: valid copy, custody-only valid copy, corrupt custody alongside valid primary, and missing all copies. Expected discovery must not invent a missing primary when custody is accepted, and must retain a malformed expected custody gap.

All other v1 conclusions remain unchanged: peer-only literal configuration replacement, shared evidence wiring, inherited identity/policy/accounting/source/delivery gates and historical STOP outcomes. Native tool-catalog removal is still unproven; this review makes no efficacy or adoption claim.

## Final resolution within the same second review round

Final verdict: **SHIP-for-native-validation** for `results/review-manifest-v3.json`, SHA-256 `ad714824352b583189b953f7e2646c1a41ad9253d4a0e9fb1cd18e7490c66b65`. The v2 findings above remain the record of the intermediate reviewed bytes; both portions of the MEDIUM are now resolved. No remaining CRITICAL, HIGH or MEDIUM finding in this targeted review.

Independent read-only hash verification found zero mismatches across all 38 files and four bound dependencies. Only `capture_discovery.py` and `test_runner.py` differ from v2. Final SHA-256 values:

- `capture_discovery.py`: `a74a17a429a4ac1c256913e264a901bdc255ffbadbf1bd3bac24bed023e7d956`
- `test_runner.py`: `0e269b2dd7907144454878a858b959da370075a17821de8051010b7755195029`

The final correction derives the custody suffix from the translated retained-relative path for absolute paths, while preserving the existing short relative `.devlyn/...` suffix behavior. `/home/participant/capture.json` therefore matches `home/capture.json` and its retained custody copies. The new fixture covers valid primary plus custody, valid custody after primary removal, and malformed remaining custody. Missing-primary-with-no-custody, unsupported home mounts, outside symlinks and relative custody cases remain covered by the retained fixtures. Code inspection confirms malformed matching custody remains expected even if a valid primary also exists.

`redirected_paths()` now canonicalizes `out` at entry as well as the collector doing so, making direct helper return paths consistent on macOS without changing containment policy. The first custody log preserves the resulting alias assertion failure; the next prediction records that root correction before the retained final run reports 41/41 PASS. This reviewer read those results and the exact final diff; no tests were rerun.

This final verdict closes the implementation review only. Native fresh/resume tool catalogs must still show that the peer's collaboration tools are absent while owner capability remains intact. Historical 0238/0240 STOP/PARTIAL outcomes remain unchanged. Registration, frozen-source/package integrity and installed binding checks remain the owner's separate prerequisites for native dispatch. No efficacy, performance or adoption claim is made.
