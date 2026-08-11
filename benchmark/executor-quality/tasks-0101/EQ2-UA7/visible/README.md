# Multi-location inventory transfer fixture

The service moves stock between locations and reports rejected transfer legs
through a separate discrepancy reporter. Destination policy is checked after
the mover reserves stock at the source.

Repair `move_batch` in `stock_mover.py` without changing the store encoding,
reporter precedence, or public result shapes. Run the suite from this directory:

```sh
python3 -m unittest discover -s tests -v
```
