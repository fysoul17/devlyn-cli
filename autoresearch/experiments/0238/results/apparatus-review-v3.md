# 0238 apparatus review v3 — bounded second round

SHIP for the two apparatus corrections. No remaining HIGH or MEDIUM finding in this bounded scope. This verdict permits proceeding with preparation and, after the owner's solo-baseline decision, authenticated native calibration; it does not admit a product instruction, register an experiment, or authorize a model call.

Reviewed 2026-10-10 against apparatus-review-manifest-v3.json and the preserved v2 source. All six frozen file hashes and the shared process dependency match. peer.py and runner.py remain unchanged from v2.

The previous findings are resolved:

- policy.py preserves failed attempts and whole-run accounting while exposing validation_completion, failed_attempts and recovered separately. Resumed and fresh successful recovery no longer permanently fail otherwise correct source/delivery. An accounted but unresolved peer failure remains separately INCOMPLETE. Source mutation and overlapping independent attempts remain protocol failures. This matches registration-proposal.md's explicit distinction between product correctness and mechanism completion; missing identity/accounting still fails closed as STOP.
- f23_precision.py emits both required supplemental FAIL rows for an existing snapshot missing the owner-editable bin/cli.js. Missing snapshot or interpreter remains apparatus STOP. The supplemental runner's existing exit/schema checks accept the product FAIL without weakening evaluator-failure detection.

Before verification, predicted the recovered and unresolved-accounted cases would preserve costs without a quality penalty, deleted CLI would yield four FAIL rows through the full checker, and absent interpreter/snapshot would remain STOP. Independently ran only the five new targeted regression cases: 5 tests passed in 5.949 seconds, exit 0. No broad suite or external model CLI call was run.

Inspected retained full-check-v4 output: no-op has four FAIL rows and delivery false; positive has four PASS rows and delivery true; deleted CLI has four FAIL rows and delivery true, correctly preserving product failure despite a matching commit. The retained missing-interpreter control exits 2 with explicit STOP. These pinned-image controls were inspected, not rerun by this reviewer.

The prior review's limitations remain: synthetic receipts do not prove current native CLI schema/effort/usage behavior; operational authenticated new/resumed peer smokes remain necessary before measurement. The registration proposal and smoke tasks remain preparation only. The owner's fresh fixed-baseline solo confirmation takes precedence over any pair model call.

## Exact reviewed identities

- `peer.py`: `d500dc6ca46c5ab1528c6d419530ad89094f36443461979c6aa1d27933fa3294`
- `policy.py`: `d02be3a1700c0a78aab0d141580da7eacc97be97a60ea7cfc27e9bd31b154606`
- `runner.py`: `c8d893bc2782d3b2f49d5bb203a471168a897ff80a5291cf0840d9093eba0a5e`
- `test_peer.py`: `c06be9e3fa81275b420f305de76aa686d22bc250d5c165aa0aa959aefff02a27`
- `test_runner.py`: `303fc5abafcd320e4c4636ff49d11a88eb2b6bec718510ef053a23e311fad719`
- `f23_precision.py`: `47124cac8635717d90d22cb5719579e611952e3925ec3ef28a2f678312fe9e89`
- `registration-proposal.md`: `7d9a07d8f643c71eaeefaae46232a85ee01eea965935607102189d190fe5de38`
- `config/skills/_shared/platform-support.py`: `a8e1472b792000bd21ef5d359eba2ae49555adcc198198f2625b51ebb94bbc66`
