# Gradebook import contract

Gradebook rows are processed by descending rank with source order breaking ties, rejected rows are reported by error precedence with student errors before score errors before rank errors and source order breaking ties, and when malformed and valid rows interleave in ranked processing the rejections retain that error precedence while malformed rows never consume placement capacity or block later valid rows.

The importer returns two lists: placed student identifiers in processing order and rejected row records in reporting order. Capacity limits placements, not validation attempts.
