"""Gate admissions are retained by the lift operations team.

The gate scanner writes one ledger entry for a pass in each lift window. A
second tap in the same window is refused, while a later window remains valid.
"""


def scan_pass(pass_record, window):
    if not pass_record["active"]:
        return False
    if window in scanned_windows(pass_record):
        return False
    pass_record["uses"].append({"pass_id": pass_record["id"], "window": window})
    return True


def scanned_windows(pass_record):
    return [entry["window"] for entry in pass_record["uses"]]


def single_use_windows(pass_record):
    windows = scanned_windows(pass_record)
    return len(windows) == len(set(windows))
