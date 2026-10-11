Fix Beacon config's reload behavior. Our supervisor sees stale settings after a
shared include changes, and a client's edits to its snapshot have leaked into
later reads. Repair include resolution, merging, and snapshot publication to
honor the existing format and reload contracts. Shared includes in different
branches must work, bad deployments must leave the last good configuration
available, and repairing a broken file must allow a later reload to recover.
Keep the exported APIs and useful ConfigError diagnostics. Run
`python3 -B checks/run_checks.py` and add focused coverage for the repaired paths.
