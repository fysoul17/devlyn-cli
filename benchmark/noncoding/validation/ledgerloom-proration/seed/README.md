# Ledgerloom — subscription billing

Turns plan subscriptions into invoices.

## Layout

- `billing/plans.py` — the plan catalogue; prices are integer cents per month.
- `billing/money.py` — `round_half_up` (integer division, ties away from zero) and
  `format_cents`. Money is **always** integer cents; floats are never allowed to
  carry an amount.
- `billing/invoice.py` — `Invoice`: lines of `(description, amount_cents)` and an
  int `total_cents()`.

## Common commands

```
python3 -m unittest discover -s tests     # run the suite
```
