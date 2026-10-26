# Contract: judge.py scratch location (operator tool)

Work in `/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0259-result` only.

Hard limits:
- Do not touch `~/.local/share/nx01`.
- Do not run Docker.
- Do not edit anything except `autoresearch/experiments/0259/results/operator/judge.py`.
- Do not commit.

Problem: on this host, Docker Desktop hangs at `containers/create` for any bind mount whose source is under `/Users`. This
survives a full Docker restart. Mounts from `/private` work. `judge.py` mounts its temporary snapshot copy from
`<runtime root>/scratch/judge` and the witness directory from the repository; both are under `/Users`.

Change, keeping behavior otherwise identical:

1. `SCRATCH` is `Path(os.environ['NX01_0259_JUDGE_SCRATCH'])` when that variable is set and non-empty. Otherwise it
   keeps today's default. If the variable is set, the path must be absolute; fail loudly if not.
2. In both `run` and `probe`, copy the witness file into the per-attempt temporary directory, as `<temp>/witness/<name>`,
   and mount that directory read-only at `/witness` instead of `witness.parent`.
   - Verify the copy's sha256 equals the source's before running.
   - Fail loudly on a mismatch.
   - Do not change the container flags, image, command, timeouts, result classes, attempt bookkeeping or output files.
3. Update the module docstring with one line documenting the variable.

Done means: `python3 -m py_compile` is clean and `python3 -m pytest -q -p no:cacheprovider autoresearch/experiments/0259`
passes. Report the diff.
