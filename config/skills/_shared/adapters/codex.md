# Codex adapter

## Invocation

A Codex executor runs through `_shared/codex-monitored.sh`, never a raw or piped
`codex exec`: `bash "$DEVLYN_SHARED_DIR/codex-monitored.sh" <arguments for codex exec> "<prompt>"`.
The `workspace-write` sandbox keeps `.git` read-only, so an executor that commits adds as
writable roots the common Git directory (`git rev-parse --path-format=absolute --git-common-dir`)
plus, in a linked worktree, its own Git directory (`git rev-parse --path-format=absolute --git-dir`),
listed exactly because the sandbox protects it even under a listed parent. It also
denies network, which installing a new dependency needs:
`-s workspace-write -c 'sandbox_workspace_write.writable_roots=["<git dir>","<worktree git dir>"]' -c 'sandbox_workspace_write.network_access=true'`.
Deliver a multiline prompt as exact file bytes: set `DEVLYN_CODEX_PROMPT_FILE=<file>`
and pass the sole prompt argument `-`.

The sandbox also denies browsers, simulators and screen capture, so a delegating orchestrator runs `python3 "$DEVLYN_SHARED_DIR/observer.py" run --spool <workspace>/.devlyn/observer --worktree <workspace> --out <workspace>/.devlyn/loop/evidence/observations -- bash "$DEVLYN_SHARED_DIR/codex-monitored.sh" …` and gives the implementer the call argv `python3 "$DEVLYN_SHARED_DIR/observer.py" call --spool <workspace>/.devlyn/observer --`; the observer returns captures only, and the implementer judges.
