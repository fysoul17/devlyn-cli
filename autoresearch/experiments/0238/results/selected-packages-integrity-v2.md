# Selected packages v2: integrity and one offline import test

2026-10-10. **PASS for the package boundary checked here.** No rebuild, model/auth/Docker call, or actual runtime staging was performed. The builder and prior archives were not modified. Baseline selection is root's accepted installer decision; S/H/P remain experimental.

Inputs: `~/.local/share/nx01/0238-live/selected-packs-v2/packages.json`, SHA256 `85f90c64181bc41b8f071d4017dc97d4e19c19d858477696a552b93ecf7ab8f7`. Predictions preceded payload comparison and execution in `selected-packages-integrity-v2-prediction.json`.

All four archives and all 969 regular-file hashes match metadata; no extras, omissions, duplicate/special members, or unexpected arm mode differences were found. An independent read-only subagent verified the payloads (`selected-packages-integrity-v2-payload.json`).

| Arm | Files | Archive SHA256 |
| --- | ---: | --- |
| B | 241 | `050bc8d6f3af071461903f0c7efd77ae445828f232152cd4f52b6e81faa967b3` |
| S | 242 | `c031f7d5e5ea752bf153092e059684f281cfd55a1241c643f57b525b22d334d5` |
| H | 243 | `1731e86ce031172ce87352146887e1ac28abbdf65266ee1cf05a28466ca53d3f` |
| P | 243 | `10a748e9235f614b0c2f8091aa17fec88a6f762d77e5d4f8a830d3dc8ddb5d5e` |

All seven copied baseline input hashes match both current accepted source and the builder's copied tree. The published canonical delivery files, `bin/instructions.js` and `package.json` also match their payload hashes. The two `.agents` mirrors and `package-lock.json` remain build inputs excluded by existing npm publication policy. Raw comparisons are in `selected-packages-integrity-v2-baseline.json`.

B versus preparation-packs-v1 B changes only `bin/instructions.js` and `package.json`, adding 16 `node_modules/marked/` files. Nothing is removed; `bin/instruction-templates.json` is unchanged. S/H/P each modify only `AGENTS.md`, `CLAUDE.md`, canonical `runtime-principles.md` and generated instruction history, and add their own `pair.md`. H/P additionally add `peer.py`. Three principle payloads append exactly the registered trigger; history adds its fingerprint once in each host array. Guide/helper bytes match current selected source.

All arms bundle the same Marked 15.0.12 with `main` and CommonJS default export pointing to `./lib/marked.cjs`, an actual `module.exports` assignment, and no runtime/optional/peer dependencies. The installed-package test below exercises that synchronous import path under Node 20.19.0.

## Offline installed B check

The first preparation failed at `npm --version`: npm rejects loading `/dev/null` as both user and global config. No installation or test had run. That failed prediction/result remains in `selected-packages-integrity-v2-test.json`. The correction was prospectively recorded in `selected-packages-integrity-v2-config-prediction.json`: a new private directory with two distinct empty private config files, without changing any host auth/config.

The corrected run used Node 20.19.0/npm 10.8.2, an empty private npm cache and `npm install --offline --ignore-scripts --no-audit --no-fund` against selected B. Installation passed. Exactly one existing targeted test then ran with `--package-root` pointing to that install:

```text
PackageTests.test_agents_imports_follow_markdown_text_and_complete_paths
Ran 1 test in 0.046s — OK
```

Its 37 Markdown/path/frontmatter controls pass. The installed 241 payload files all match B's recorded hashes; the source test and B archive remain unchanged. Full commands/stdout/stderr and timing are retained in `selected-packages-integrity-v2-test-config1.json`. Both fresh private directories remain under `0238-live/selected-package-audit-v2*`; no prior workspace was reused or removed. This does not replace selected-runtime calibration, H/P native smokes, or model-effectiveness evidence.
