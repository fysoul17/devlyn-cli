def ledger_total(rows):
    return sum(row.get("units", 0) for row in rows)
