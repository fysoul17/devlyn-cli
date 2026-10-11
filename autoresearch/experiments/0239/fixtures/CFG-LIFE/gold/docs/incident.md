# Supervisor incident notes

Editing a shared defaults file did not update either application's settings,
although the watcher called reload. Replacing the root was the only way to
unblock it. The rollback UI also showed settings edited by a consumer rather
than the last published configuration. The include cache was added for startup
speed when several applications share defaults. There is no performance target
that requires keeping file contents across reload calls.

The next deployment will add diamond-shaped includes (regional defaults and
service defaults share a base), so shared includes must remain legal. Operators
need the failing path and include chain when a deployment references a broken
file; publishing a partial configuration would make diagnosis harder.
