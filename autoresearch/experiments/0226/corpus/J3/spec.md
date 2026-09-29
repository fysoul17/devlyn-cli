---
id: "J3"
title: "Restore artifacts when speculative validation rolls back"
kind: feature
status: planned
complexity: high
depends_on: []
---

# Restore artifacts when speculative validation rolls back

## Context

Joi artifacts identify successful schema validations and record the paths that produced them. A branch or candidate can collect artifacts before later validation causes that attempt to be discarded. Callers need the returned artifacts to reflect the retained validation result, so artifact collection must participate in Joi's existing validation transactions.

## Requirements

- [ ] Artifacts collected by an attempt discarded through the existing snapshot/restore lifecycle must not appear in the retained result. This applies to unsuccessful alternatives and array item candidates, condition probes whose state is restored, and failed validation replaced by failover.
- [ ] Rolling back a validation attempt must remove every artifact path collected during that attempt while preserving all artifact paths that existed at its start, including paths stored under an artifact id reused inside the attempt.
- [ ] Committing a successful validation attempt must retain its artifacts together with earlier artifacts, including all committed paths associated with a shared artifact id.
- [ ] Preserve the artifact map's identifier identity, identifier insertion order, and path order. Keep the existing map-of-path-arrays format in synchronous results and in asynchronous results requested with `artifacts: true`.
- [ ] Restoring an attempt that began without an artifact map must restore that absence; a successful result with no retained artifacts must omit the `artifacts` field.
- [ ] Update the `any.artifact()` documentation in `API.md` to explain that discarded speculative validation does not contribute artifacts to the retained result.

## Constraints

- Change only `lib/validator.js`, `test/base.js`, and `API.md`, because artifact transaction bookkeeping can be added without changing schema APIs or their callers.
- Use the existing snapshot, restore, and commit lifecycle, because alternatives, array matching, condition probes, and failover already define which validation work is retained.
- Preserve existing validation values, errors, warnings, external-method scheduling, and other transaction state, because this change concerns artifact reporting only.
- Add no dependencies and keep the existing test, coverage, lint, and type-check configuration unchanged, because this behavior belongs in the current validator and must meet the repository's existing checks.

## Out of Scope

- Changing artifact reporting for ordinary root validation failures that do not restore a validation snapshot.
- Adding artifact options, changing artifact identifiers, or changing the result format.
- Refactoring branch selection, array matching, condition evaluation, or failover behavior.

<!-- devlyn:verification -->
## Verification

- `npm test` exits 0 from the repository root, offline, under Node 22 with the installed development dependencies. Its existing Lab suite, 100% coverage threshold, lint, and type checks must pass. Add public tests for discarded alternatives with no prior artifacts; prior artifacts followed by a discarded branch and a committed branch, checked synchronously and asynchronously; a failed object replaced by failover while an earlier artifact survives; and a successful alternative appending a committed path to a shared artifact id.

Source review must confirm the requirements beyond these test scenarios, including restoration and commit across the existing transaction callers, preservation of prior artifact state through repeated or nested attempts, identifier identity and ordering, and unchanged validation side effects. Review the documentation for agreement with the transaction scope.
