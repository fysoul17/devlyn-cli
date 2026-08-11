# Order return fixture

The service accepts a batch of return requests, records refunds in a small
file-backed order store, and reports rejected requests through a separate
reason ranker.

Repair `process_returns` in `refund_engine.py` without changing the public
models or store encoding. Run the suite from this directory:

```sh
python3 -m unittest discover -s tests -v
```
