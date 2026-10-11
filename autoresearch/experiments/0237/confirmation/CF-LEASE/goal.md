Fix the durable delivery bugs in Parcel relay. After a worker times out and a new
worker takes its job, a late success or failure from the original worker can
currently settle the new attempt. Producer retries can also revive a completed
job. Make retries, lease expiry, and worker results obey the existing delivery
and persistence contracts, including recovery through a newly opened database
connection. Preserve the public APIs and keep errors visible to callers. Inspect
the package's operational docs and call sites, make the repair, and run
`python3 -B checks/run_checks.py` plus focused tests for the repaired behavior.
