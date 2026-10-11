# Direct AGENTS import dedup — bounded follow-up v2

2026-10-10. SHIP. The v1 HIGH is fixed; no remaining HIGH or MEDIUM finding in this narrow follow-up. This concludes the second review round. Scope is the native frontmatter exclusion and its regressions, retaining the previously reviewed detector/dependency/ownership design.

The detector now removes BOM and the exact pinned-native prefix `/^---\s*\n([\s\S]*?)---\s*\n?/` from its temporary parsing string before Marked lexing. It does not edit the original source or ownership/update/backup paths. The prefix follows the native memory pipeline even for malformed YAML, while an absent closing delimiter leaves ordinary Markdown available. This eliminates the demonstrated false import that could remove CLAUDE's sole effective defaults. The native byte offsets and reproduction remain in import-dedup-review-v1.md; its finding has not been overwritten.

Before independent checking, predicted three frontmatter-only cases would return false and the real body-import/unclosed-prefix cases would return true. Local Node detector invocation exited 0 with:

```jsonl
{"name":"frontmatter","expected":false,"actual":false}
{"name":"bom-crlf","expected":false,"actual":false}
{"name":"malformed","expected":false,"actual":false}
{"name":"body","expected":true,"actual":true}
{"name":"unclosed","expected":true,"actual":true}
```

The added portability cases cover these five boundaries and a real frontmatter-only install retaining CLAUDE defaults and prose across reinstall. The owner's full PackageTests v2 run was still in progress when this review was written; this report does not claim its result. Full-test completion and distribution validation remain owner delivery checks. No models, native Claude/Codex CLI, authentication or Docker calls were made; no product files were edited by the reviewer.

Exact reviewed v2 identities:

- `bin/instructions.js`: `c2ef3fda7714efab8e1569a4d08ec17abc1a10469133b11b159d0884f7bb2532`
- `package.json`: `ffaaffe502f9c77faa7c0e3dfa2c261373e15ff907d15acf16e96bc604919c07`
- `package-lock.json`: `673daed9c547a038027950cfd31a1fa2144639982a8299a37184d5f0d2c7ae8d`
- `scripts/test-windows-portability.py`: `8497a6a228fd7f1bc1bdd3fc63121b1eb6e902879f3d64ac8c1d7fd367b0b6a7`
