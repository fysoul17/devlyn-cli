def tier_invoice(batch):
    readings = [entry for entry in batch["readings"] if "cumulative" in entry]
    series = [entry["cumulative"] for entry in readings]
    if series != sorted(series):
        return {"valid": False, "series": series, "adjusted_usage": None, "recomputed": []}
    adjustments = [entry["usage_delta"] for entry in batch["readings"] if entry.get("kind") == "adjustment"]
    keys = []
    for entry in batch["readings"]:
        if entry.get("kind") == "adjustment" and entry["rebill_key"] not in keys:
            keys.append(entry["rebill_key"])
    usage = series[-1] - series[0] + sum(adjustments)
    return {"valid": True, "series": series, "adjusted_usage": usage, "recomputed": keys}


# The tierer reads an ordered cumulative ledger before it assigns tier bands.
