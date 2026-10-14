I'll review commit `5704f5b9` against `DESIGN.md` on the six contract points, starting with the design, the diff, and how this apparatus loads the frozen rp-d1 modules.The adapter loads rp-d1 by path and patches its globals. I'll compare those call sites with the frozen modules so a wrong module identity can't hide an arm or schedule mix-up.The arm label written into `plan.json` is not the label the frozen peer check still enforces. Every live cell stops after dispatch, before delivery grading.

## HIGH

**`prepare.py:80` writes arm `X` or `Y` into `plan.json`, and the frozen checker still only accepts `A`/`B`/`S`.** `0242/policy.py:45-48` returns immediately only for those three arms. Any other arm indexes `tasks['routes'][config]['peer_routes'][arm]`. rp-d1 tasks have only `owner`, so that lookup raises `KeyError: 'peer_routes'`.

`0242/policy.py:110` is the call. It uses the `route_for` global in that module. `0240/runner.py:22-23` reaches it through `base_policy.check`, and `0242/runner.py:20-22` rebinds that module and the `policy.route_for` attribute. `rp-d1-delivery-cost/runner.py:55` replaces only the attribute, which is what `0238`’s initializer calls. It does not replace the global `check()` calls.

Failure: slot `m01` (arm X, Claude or Codex) installs the X package and passes binding, then the owner runs. `0255/runner.py:113` (Claude) or `0238/runner.py:153` (Codex, via `0255`’s `super().run`) calls `policy.check` on that plan. `KeyError` becomes an inherited `STOP`. rp-d1 records `STOP`, archives and deletes the repo if teardown was clean, and the schedule writes `NOT_RUN` for the rest. No attempt reaches delivery grading. `stage.py --check` and the runner tests do not call this path: the lifecycle test replaces `0255`’s `run`.

## Rest of the contract

Arm mount, baseline binding, and launch re-check select `packages/X` or `packages/Y` and compare the installed `task-completion.md` to that arm. Schedule order, smoke names, `STOP`/`NOT_RUN`, remaining-repo precheck, prior deletion, archive-then-404, and the PAT scan stay on the rp-d1 functions. Renewal is only at an even measured prefix, same account pair, with the inherited 6300-second floor on `auth.preflight` at launch. Records store the auth path and hashes, not the token. The adoption rows match the zero-success, compared-cost `UNKNOWN`, quality, and cost rules.

The `runtime['release'] = X` shim exists so rp-d1 `inputs()` can hash a tarball. Install does not use it. `pack.py:102`’s `diff(after) == diff(expected)` is redundant once `after == expected`.

VERDICT: REVISE
