# Beacon config

Beacon config loads a deployment's JSON settings from reusable include files.
The long-running supervisor owns one ConfigManager and calls reload when its
watcher sees changes. Clients consume detached Snapshot objects; a failed reload
must leave the last usable snapshot available to the supervisor.

Python 3.11+ standard library only. Run `python3 -B checks/run_checks.py`.
The format, reload, and error contracts live in docs/. The sample application
uses the real manager API and is safe to run locally.
