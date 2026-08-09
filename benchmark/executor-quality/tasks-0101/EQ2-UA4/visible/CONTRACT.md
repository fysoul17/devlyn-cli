# Invoice intake contract

Invoice lines are posted by descending priority with source order breaking ties, parsing rejects are reported with format errors before account errors before amount errors and source order breaking ties, and when malformed and valid lines interleave each posting records the cumulative amount of valid lines in posting order while rejects retain their own precedence without advancing that total or preventing later valid postings.

Each input line uses `invoice|account|amount|priority`. Invoice identifiers use one
uppercase letter followed by three digits, accounts use `acct-<name>`, amounts are
positive decimals, and priorities are integers.
