# iter-0057 — delete ollama/vllm local-backend engine product surface

**Status**: DRAFT-IMPLEMENTED (awaiting review). Not committed.

**Trigger**: iter-0055 (JUDGE-QUALITY) measured `ollama/gemma3:4b` as VERIFY
pair-judge: 100% false-positive rate (would flip every pair-triggered VERIFY
to NEEDS_WORK regardless of diff quality). iter-0056 (JUDGE-INVOCATION-RESHAPE)
tried 3 invocation reshapes (calibration+few-shot, enumeration schema,
two-pass triage) — all failed, closing the question as **model ceiling at 4B
for this role, not an invocation-shape gap** (V3's apparent FP=0 proven a
pass-1-always-false orchestrator artifact, not model discrimination).
Adversarial pair review (GPT-5.5) concurred: "pin-eligible routes require
measured non-harm — delete or quarantine the local-backend product surface
now; the exposed route is the failed model; vLLM is recommend-only with no
route."

## Deletion ledger

| File | What | Why |
|---|---|---|
| `_shared/adapters/ollama.md` (+ 2 mirrors) | Deleted whole file (33 lines) | The failed adapter itself — judge-only route measured non-viable |
| `_shared/engine-doctor.sh` (+ 2 mirrors) | Removed `ollama`/`vllm` from `TARGETS`/`KINDS`/`BINARIES`/`INSTALL_HINTS`; deleted `SERVER_URLS` array + `check_server()` (now unused — no remaining target is server-backed); deleted the `local-backend` case branches from both pin-eligibility and note logic; dropped the now-always-`n/a` `server` column from the printed table | Local-backend detection/pin-eligibility/recommendation logic is dead once no local-backend target remains — leaving it would print a column that's always empty |
| `_shared/adapters/README.md` (+ 2 mirrors) | Removed `(e.g. Ollama)` citation from the `## Invocation` bullet | Named example pointed at a now-deleted file |
| `_shared/engine-preflight.md` (+ 2 mirrors) | Removed `(e.g. \`ollama\`)` citation from the Role eligibility paragraph | Same — stale concrete example |
| `devlyn:engines/SKILL.md` (+ 2 mirrors) | Target list `claude/codex/omp/pi/ollama/vllm` → `claude/codex/omp/pi`; "binary/server is present" → "binary is present"; dropped "or \`local-backend\`" from the pair-judge row description; dropped "e.g. \`ollama\`" from the executor-pin refusal example | Doc described a detection surface that no longer exists |

## Kept — not deleted (judgment calls)

1. **`## Role eligibility` / `## Invocation` adapter-extension mechanism**
   itself (README.md format spec, `check_role()` in engine-doctor.sh,
   engine-preflight.md's role-resolution rule) — kept. This is documented as
   general plug-in infrastructure ("the plug-in point future local backends
   ... reuse without further skill changes", iter-0051), not ollama-specific
   product surface. Scope was "product surface only"; only concrete
   ollama-naming citations were removed, not the extensibility contract.
   Consequence: `judge-only`/`executor-only`/`none` role values are currently
   unreachable (verified: claude.md/codex.md/omp.md declare no `## Role
   eligibility` section) — mechanism is dormant, not dead, pending a future
   adapter.
2. **`adapters/README.md`'s "Qwen / Gemini / Gemma ... (Mission 2/3)"
   roadmap sentence** — kept. Refers to hypothetical future adapters for
   those model families via whatever route they'd ship with, not the deleted
   local Ollama HTTP-server route.
3. **`scripts/lint-skills.sh`** — no changes needed. Grepped for
   ollama/vllm/local-backend/gemma/pin_eligible/Role-eligibility-specific
   checks: zero hits. `critical_path_files` never included `ollama.md` or
   `engine-doctor.sh` (iter-0051 documented this exclusion as pre-existing,
   inherited from iter-0050) — nothing to delete or update there.
4. **`.devlyn/engines.json`** — checked, not present on this machine. No pin
   to report or leave alone.

## Token gauge (`scripts/skill-token-gauge.py`)

| | lines | chars | (2 token-count columns) |
|---|---|---|---|
| `_shared` SUBTOTAL before | 721 | 59,529 | 14,881 / 10,234 |
| `_shared` SUBTOTAL after | 688 | 56,663 | 14,164 / 9,789 |
| GRAND TOTAL before | 10,655 | 561,243 | 140,289 / 95,934 |
| GRAND TOTAL after | 10,630 | 559,896 | 139,951 / 95,798 |

Note: root `CLAUDE.md`/`AGENTS.md` changed concurrently (a different in-flight
task in this session, confirmed via harness system notice — not this
iteration's edit), so GRAND TOTAL's net delta mixes both; the `_shared`
subtotal isolates this iteration's actual effect (-33 lines / -2,866 chars).

## Verification

- `bash scripts/lint-skills.sh` → **"All checks passed."**, exit 0. (One
  pre-existing, unrelated gap surfaced in the log: `rg: command not found` at
  line 963 — ripgrep isn't installed here; that check still reported ✓
  overall. Not caused by, or fixed by, this change — flagged, not touched.)
- `bash config/skills/_shared/engine-doctor.sh` runs clean (exit 0), prints
  `claude`/`codex`/`omp`/`pi` only, zero ollama/vllm/gemma/11434 mentions.
- Mirror parity: `diff -rq config/skills/_shared {.claude,.agents}/skills/_shared`
  and same for `devlyn:engines/` — both clean.
- Residual grep (`ollama|vllm|11434|local.backend|gemma`, product surface):
  6 hits, all judgment-call keepers above (2 files × 3 mirrors). `benchmark/**`
  (4 files) + `autoresearch/**` (11 files) hits are the protected measurement
  archive, untouched per scope.
