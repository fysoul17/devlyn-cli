# CFG-LIFE: exposed development diagnostic

This is a new fixture identity for a prospective native-child lifetime experiment. It is not a retry, regrade, fresh confirmation, or evidence for admitting a harness change. The 0237 CF-CONFIG artifacts and results remain unchanged. No model, authentication, network, Docker, or product calls were made for these controls.

Only `goal.md` and `visible/**` belong in the participant request/source. `hidden/**`, `gold/**`, controls, this audit, and all metadata are evaluator material and must stay outside participant mounts. The 19 visible files, goal, and copied gold are byte-identical to the original revision-2 fixture. `integrity.json` records every equality and confirms all 43 files bound by the original fixture manifest still match it.

- Visible tree SHA256: `cde326d7b3178c800f59d15d7d8ced54b867f4604d72d2d057eda60b613b8815` (canonical path/hash map encoding specified in `integrity.json`).
- Goal SHA256: `a9a647fc5235aa4c962bfd0235816b34af1fbb5b32fdf825f044c7c20c133a79`.
- New oracle SHA256: `86967bc80597beee6ab6e37c272c0c58ef636498b13f5a31512f233c10323d22`.
- Pre-control prediction SHA256: `c14520180a23ecc970f302e001db592c09b4d800d55b5152838dabfc773d1a33`.

## Assertion provenance

`hidden/assertion-provenance.json` enumerates all 41 static assertions plus explicit rejection branches, exact source lines, hashes, and quoted public bindings. Controls passing are not used as provenance. `F` means `visible/docs/format.md`; `R` means `visible/docs/reload.md`.

| Oracle row | Public obligation checked |
| --- | --- |
| `loader-merge-value-kinds` | F10–16: ordered layers, recursive objects, replacement for other kinds, list replacement, ordinary null. One nested case plus all 36 earlier/later object/list/null/string/number/boolean combinations run through exported `Loader`. No private helper is imported or assigned an ownership rule. |
| `relative-diamond-layer-order` | F10–16,18–23: declaring-parent paths, ordered diamond reapplication/local override, canonical complete sorted dependencies. Exported `Resolved.dependencies` is a tuple of Paths. |
| `transitive-change-same-size-and-mtime` | R3–8,16–24: content freshness despite unchanged metadata, value-based generations, prior snapshot isolation. Oracle line98 checks the fixture's equal-size precondition. |
| `nested-caller-isolation` | R16–24: nested mutations of reload/current/Loader results do not leak into stored state or future results; equal values preserve generation. |
| `semantic-generation-current-dependencies` | R3–8,16–19 and F21–23: first generation1; equal/format/dependency-only changes keep generation; changed values advance; dependencies refresh. |
| `failed-reload-preserves-and-recovers` | R10–19 and F7–16,21–23: failed graph does not publish, path/chain identify missing file, repair yields correct values/dependencies and generation. |
| `failed-first-load-no-cache-poisoning` | R3–18,25: no current before success; partial failed graph is not reused; repair sees changed earlier branch and starts generation1. |
| `deleted-dependency-repair` | R3–14 and F7–8: missing dependency is observed, last good state remains, repair recovers. |
| `canonical-cycle-after-success` | F7–11,18–19 and R10–14: active canonical stack recurrence fails with path/chain, preserves state, then recovers. No exact English reason word. |
| `repeated-include-public-freshness` | F18–19,21–23 and R3–8,21–24: canonical alias is legal, unique dependencies, fresh later call, first result remains intact. This row does not count reads. |
| `independent-root-dependency-accuracy` | F21–23 and R3–8: later independent root gets its own values and dependency graph. |
| `schema-errors-retain-include-chain` | F3–8 and exported `ConfigError.path/chain`: invalid schema/JSON fails at the canonical leaf with root-to-failure chain. No exact rendered message or punctuation. |

`same_json` separates JSON booleans from numbers while accepting equal integer/float representations. All source-facing oracle calls use exported `Loader`, `ConfigManager`, or `ConfigError`. Internal subtree sharing is allowed; only the documented public returned-value boundaries impose isolation.

## Prospective controls and raw results

`prediction.json` was written before the first control execution. Run command:

```sh
python3 -B autoresearch/experiments/0239/fixtures/CFG-LIFE/validate.py --out autoresearch/experiments/0239/fixtures/CFG-LIFE/controls/run-1
```

The retained directory is immutable evidence; repeat with a new output path. The validator refuses an existing output directory. `controls/run-1/*-{public,oracle}.json` retains commands, return codes, complete stdout/stderr; `summary.json` records host Python3.14.7/macOS26.5.1 and prediction hash. These are host controls, not pinned-image calibration.

| Control | Public | Oracle | Meaning |
| --- | --- | --- | --- |
| Original visible baseline | exit0 | 1/12 | Only schema diagnostics pass. |
| Copied gold | exit0 | 12/12 | Positive execution control, not proof of contract validity. |
| Internal-sharing alternative | exit0 | 12/12 | Recursive helper shares input list identities without mutating either input; public Loader/manager boundaries remain detached. Separate retained probe confirms both aliases exist. |
| No-read metadata-open alternative | exit0 | 12/12 | An additional open/close without reading is permitted; one actual document read remains. |
| Alternate cycle wording | exit0 | 12/12 | `circular include` with preserved path/chain is accepted. |
| Shallow-merge negative | exit0 | 10/12 | Only new value-kind and diamond rows fail, as predicted. |
| Rereading negative | exit0 | 12/12 | Known false negative, deliberately retained to demonstrate the coverage gap below. |

All predictions matched. The alternatives are new hidden research controls built over copied gold; no historical participant source or historical result was regraded.

Pinned-image calibration also matched all seven predictions without source/oracle changes. `prediction-pinned.json` preceded execution (SHA256 `a63f92b9af0f6ad21ada6893bdf05e1d8b790609058e857a0944bf7e11e29dda`). Image `sha256:0f472bb41685b7daa5923d51d31983f4b3c70053dd773fdf712bd0dcd6d87998` ran Python3.12.14 under `--init --network none --read-only`, with the fixture mounted read-only and temporary control source copies in `/tmp`. The only writable bind was the evaluator evidence directory. `controls/pinned-launch.json` retains the exact Docker command/stdout/stderr and successful container-removal check; `controls/pinned-run-1/` retains all per-case raw results. Launch exit0, empty stderr, all public exit0, all predicted row counts matched, and the named container was absent afterward.

## Limits

F20–21 still requires at most one document read and consistent bytes per file within a load. This oracle does not measure either property. Its rereading control violates the read-count obligation and still passes because test files do not change during an invocation. An exact `open` event count is not equivalent to a document-read count, so that former proxy was removed without weakening the visible contract or adding a tracing framework. Passing all rows is not proof of the entire visible contract.

The oracle also does not prescribe internal merge-result ownership, a cache representation, or exact error wording. It samples public behavior rather than proving all graph/schema inputs. The inherited protocol emits product row results as JSON with exit0 even for a failed row; import/protocol failures must remain apparatus failures at the runner boundary. Unexpected environmental failures in row details need adjudication, not automatic attribution to source quality. Registration and integration with the owner runner remain root-owned prerequisites before any model experiment.

Bounded independent static assertion review returned SHIP, HIGH0/MEDIUM0 for the oracle hash above (`review.md`). That finding concerns contract support only; it is neither cross-model strategy advice nor candidate admission.
