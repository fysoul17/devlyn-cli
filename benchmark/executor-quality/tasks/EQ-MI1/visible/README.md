# Event bus

`event_bus.py` provides a process-local handler registry. Register handlers with a name and priority, then dispatch an event to every registered handler.

Run the test suite with:

```sh
python3 -m unittest discover tests
```
