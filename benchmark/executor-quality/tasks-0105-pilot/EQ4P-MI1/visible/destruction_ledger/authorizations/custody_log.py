"""Record custody details for notes held from circulation."""


def custody_entry(note, reason):
    return {"note": note, "reason": reason}
