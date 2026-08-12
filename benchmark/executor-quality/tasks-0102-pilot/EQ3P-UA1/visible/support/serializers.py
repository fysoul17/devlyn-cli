def compact(record):
    return ";".join(f"{key}={value}" for key, value in sorted(record.items()))
