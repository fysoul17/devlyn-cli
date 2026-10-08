# 0235 apparatus: differences from 0233

Two installed arms use the same native prompt and `-y --claude`; configuration is claude only.

| Arm | Commit | Pack SHA-256 |
|---|---|---|
| B | `dd4957775337e597f39838fa73acd5c7ec4a5699` | `6f03f5ac2895eaccc22ff12d1644a0fc623baca1eec7d00e877ce3254d33352d` |
| R | `59ed8a3339316d68290afcf5b74cae0defb84dcf` | `90f041bf3f650ca3f028ba6288b4c38bd29a198dd5f76a29163e3e1ce1eb89f7` |

D3 and D4 are measured twice per arm. E1 is one unmeasured smoke cell. E1 reuses `autoresearch/experiments/0233/sources/E1`, `autoresearch/experiments/0233/calibration/E1`, and `autoresearch/experiments/0233/oracle.js` by path. D3 and D4 use the unchanged 0222 sources and evaluator.

The A and C arms, guide diagnostics, screening, easy and confirmation panels, I0185/B5/E2/F10/F11/SMOKE tasks, and vendor manifest are omitted. The decision rule is in registration `autoresearch/iterations/0235-definition-of-done.md` §5.

0233's E1–F11 sources now commit `node_modules/qs/dist/qs.js`: their own `dist` ignore rule had left the sealed file untracked. Root force-added the byte-identical file, matching the registered `source_sha256`.
