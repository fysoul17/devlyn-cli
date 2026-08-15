def new_batch(readings):
    return {"readings": [dict(reading) for reading in readings]}


def submit_correction(batch, meter_id, observed):
    for index, reading in enumerate(batch["readings"]):
        if reading["meter_id"] == meter_id:
            batch["readings"][index] = {
                "meter_id": meter_id,
                "cumulative": observed,
                "recorded_at": reading["recorded_at"],
            }
            return True
    return False
