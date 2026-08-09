# Invoice intake contract

Invoice lines are posted by descending priority with source order breaking ties, parsing rejects are reported with format errors before account errors before amount errors and source order breaking ties, and when malformed and valid lines interleave the rejects retain that precedence while rejected lines never suppress or occupy positions among valid postings.

Each input line uses `invoice|account|amount|priority`. Invoice identifiers use one
uppercase letter followed by three digits, accounts use `acct-<name>`, amounts are
positive decimals, and priorities are integers.
