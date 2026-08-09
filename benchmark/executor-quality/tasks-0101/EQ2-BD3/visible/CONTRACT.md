# DNS zone editing contract

Record applier candidates are processed by descending deployment priority with source order breaking ties, syntax ranking reports rejected changes by owner errors before type errors before value errors and source order breaking ties, and when malformed and valid changes interleave under that processing order the ranked rejection report preserves that error precedence while a rejected change never reserves its owner or prevents a later valid record for that owner from being placed.

The editor returns placed change identifiers in processing order and rejected changes in reporting order. A successfully placed record owns its name for the remainder of the batch.
