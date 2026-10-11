# 0251 — Fixed authentication for prospective solo comparisons

0249 and 0250 stopped because per-cell preflight selected a changed shared Claude
login. This adapter removes that mutable selection. It changes no task, harness
wording, model, effort, usage accounting or efficacy gate. Earlier studies remain
closed; this directory does not register another efficacy study.

Prediction, before tests: a one-time private snapshot keeps the selected account
when the host login changes. Missing or altered files, a mismatched profile or less
than 6,300 seconds of real token lifetime refuse before preparation. A second
check after preparation refuses before launch. Synthetic launch comparison will
show only the registered authentication transport delta while preserving the
5,400-second owner watchdog and native identity/evidence inventory.

Claude uses the supported `CLAUDE_CODE_OAUTH_TOKEN` interface, with original scopes,
subscription type and rate-limit tier. A private Docker `--env-file` keeps values
out of plans and recorded arguments. No Claude refresh credential is copied into
the cell. The pinned 2.1.296 source gives this route no refresh token and declines
ordinary 401 credential substitution. Expiry remains an external preflight gate;
native `expiresAt:null` does not grant unlimited lifetime. Provider revocation
can still stop execution. See the official [environment reference](https://code.claude.com/docs/en/env-vars).

The environment is visible to container processes and Docker. Raw outputs remain
private; scan selected evidence before publication, preserving any affected raw
capture privately instead of rewriting it. Teardown requests only container
state, not secret-bearing Docker configuration.

Codex's credential snapshot is separately sealed and mounted read-only. Its
existing managed-auth route remains refresh-capable and depends on the shared
grant's server-side lifecycle. Codex 0.162.1 exchanges a refresh token before
persisting it; read-only storage does not prevent that exchange. This adapter
promises stable credential selection, not independent grants or immunity to
provider revocation. No observed Codex refresh failure licenses a larger auth
redesign. Native auth faults remain STOPs, with cost retained and no replacement.
See the [pinned Codex manager](https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/login/src/auth/manager.rs).

Provision once from the default macOS host sources with
`python3 auth.py <fresh-private-directory>`; explicit source overrides refuse.
Bind the returned
manifest hash and account in a new runtime's `auth_manifest_sha256` and `account`,
with `auth` pointing to that directory. `runner.py` retains the previous single
cell CLI; separate model assessment is intentionally unavailable. No renewal,
account replacement, host fallback or automatic scheduling occurs.

Before another native run, register its operational prediction, fixed credentials,
sequence and stopping conditions. Apply identical authentication to both arms.
An authentication smoke supplies no S/B efficacy evidence. A new comparison must
acknowledge prior OR1/OR2 exposure and preserve every partial/unknown cost.

This applies **No workaround**, **No overengineering**, **No guesswork** and
**Production ready** without adding always-loaded harness instructions.
