# Supervisor reload contract

Every call to Loader.load observes current dependency contents. Atomic file
replacement may preserve size and mtime, so metadata alone is not proof of an
unchanged dependency. Dependencies may be added, removed, missing, or repaired
between calls. There is no promise of an atomic view across unrelated writers;
each individual file's first read in a load defines its contents for that load.
An invocation must not reuse values resolved from an earlier invocation.

ConfigManager.reload publishes a new Snapshot only after the entire include
graph is valid. A failed reload raises ConfigError and leaves `current` exactly
as it was. After the bad file is repaired a later reload must succeed; failure
is not sticky. Failed graphs must never partially alter old settings or the
last successful dependency list.

The first successful snapshot has generation 1. Thereafter increment generation
only when the effective merged values change. A dependency-only or formatting
change still refreshes the dependency list but keeps the generation. Generation
is used to decide whether to restart application services.

All returned values are detached: mutating a Loader result, reload result, or
current Snapshot, including nested dictionaries and lists, cannot affect future
loads, the manager's stored state, or another caller's snapshot. A frozen
dataclass alone does not provide this guarantee for its nested JSON values.
`current` is None before the first successful reload. Preserve exported APIs.
