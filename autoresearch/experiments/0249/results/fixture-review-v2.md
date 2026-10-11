# 0249 fixture review v2 — M1 closure only

**SHIP. M1 closed; zero HIGH/MEDIUM findings in the changed lines.** This is the requested narrow recheck, not a second full fixture review or pinned-evaluator admission. V1 report and evidence remain intact.

Compared three files against `fixtures/history/v1`: OR1 visible/gold `folio/storage.py` and `hidden/oracle.py`. The two storage files are byte-identical. The only product change is a named `parse_constant` callback that raises ValueError; the existing exception boundary converts it to StorageError. This rejects nonstandard NaN/Infinity/-Infinity literals without imposing a new numerical magnitude policy. M1's demonstrated nonstandard-token defect is resolved. The original note about overflowed standard numeric literals is not promoted into a new range requirement.

The additional assertions in `OR1/hidden/oracle.py:258–267` are supported by C5's malformed-file and recovery behavior and C3's no-edit commit behavior: public read and refresh reject each malformed token, preserve bytes/prior view, recover after restoring valid bytes, then permit a no-edit commit. No new private fault injection, timing assumption, or contract assertion was introduced.

No guesswork: wrote `fixture-review-v2-evidence/prediction.json` before one independent public-API check. Raw structured result is `result.json`: all three tokens rejected by both read and refresh, bytes and prior view preserved, ordinary nested finite numbers and quoted token strings still accepted, repaired no-edit commit succeeded. No full suites were repeated; author calibration and actual pinned-evaluator calibration remain their owners' responsibility. No fixture files were modified by this reviewer.

Changed-file SHA-256 values match at review start/end (`start-hashes.json`, `end-hashes.json`):

- OR1/visible/folio/storage.py: `69f1a876669f78a3f394f028e89de2c3f8f59a1d6aa0bb8dedf8c9c415da9b5d`
- OR1/gold/folio/storage.py: `69f1a876669f78a3f394f028e89de2c3f8f59a1d6aa0bb8dedf8c9c415da9b5d`
- OR1/hidden/oracle.py: `616987477897d0234e78c7749879ba2ba039eca0524498042fd763cbe4d0678c`

The v2 package seal/calibration metadata were still being prepared during this check; this review binds the three exact code files above. Parent should confirm their hashes in the final package seal. V1's inherited evaluator raw-nonzero classification caveat remains unchanged.

Final seal follow-up: fixture-manifest-v2.json SHA-256 `d246a3212afb190b4a3dc608fd3e6797ebe571c5362bf91da970088ac83f895a` matches the author announcement, is byte-identical to canonical fixture-manifest.json, includes the three reviewed file hashes, and all three current source hashes still match the reviewed bytes.
