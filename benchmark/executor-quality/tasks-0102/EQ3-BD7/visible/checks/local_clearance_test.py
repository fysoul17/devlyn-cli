def local_receipt_is_clear(receipt, closure, finding_id):
    state = next(item["state"] for item in closure["findings"] if item["id"] == finding_id)
    return receipt["cleared"] and receipt["finding"] == finding_id and state == "clear"
