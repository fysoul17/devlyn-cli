def open_count(closure):
    return sum(item["state"] == "open" for item in closure["findings"])
