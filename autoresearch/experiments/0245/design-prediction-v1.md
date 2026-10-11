# 0245 helper-owned custody repair

Registered at 2026-10-10T18:20:34.611041+00:00 before implementation or new tests.

Observed: 0243 d02 obeyed the helper API but ignored guide retention instructions:
TemporaryDirectory cleanup removed the only attempt/completion/native capture.
The unchanged collector correctly stopped. Preserve that STOP, unknown residual
and lower-bound costs; do not salvage/regrade it or dispatch remaining 0243 cells.

Decision: remove the unshipped candidate helper's --out argument. Allocate each
call exclusively under the repository's ignored .devlyn/pair/ using a unique
helper-owned directory. Return canonical receipt and answer paths. Refuse a
symlinked/escaped or nonignored custody root before dispatch; never edit ignores
or fall back. Write attempt and untouched native streams directly there before
any native execution; retain failures and interrupted calls too. Keep schemas,
argv, source snapshot, accounting and collectors unchanged. Guides lose the
output-path parameter and describe returned retained paths. There is no export
copy, second authoritative inventory, compatibility shim or new configuration.
This unshipped API has no user compatibility requirement; caller-owned prompt
and optional answer copies may still be temporary. This fixes ordinary output
cleanup, not deliberate deletion by a same-permission owner.

No workaround: fix the lifetime contract, not collector acceptance. No
overengineering: subtract the caller-selected output flag instead of adding
export/fallback branches. Best practice: standard exclusive directory creation.
Production ready: fail before dispatch if durable custody cannot be established.

Falsifiable predictions: (1) caller TemporaryDirectory exit removes its prompt
and any copied answer but leaves exactly one complete native custody set, with
source identity unchanged; (2) nonzero, timeout and interruption retain their
native streams and completion; (3) repeated/resumed calls have distinct records;
(4) invalid custody or removed --out is rejected without native dispatch;
(5) native argv, answer decoding and source-change detection remain unchanged.
Run meaningful fake-native functional tests and one bounded cross-model review
in parallel. Then register one operational Codex-owner/Claude-peer cell with
fresh/resume and caller scratch cleanup; exact inputs and gates frozen first.
No changed discovery/accounting or inference of missing usage. Native success
is operational evidence only, not automatic activation or efficiency proof.

A separate prospective adaptive diagnostic continuation may reuse 0243 d01 S
only if all relevant inputs remain identical, single-counted regardless of its
result. It must retain old d02 costs, identify revised H/P packages and fix the
remaining order before dispatch. No efficacy continuation is registered here.
