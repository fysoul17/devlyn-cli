"""Record adoption decisions at the shelter intake desk."""


def open_case(animal_id, ready, outside, history_hold, receipt, fee_cents):
    return {
        "id": animal_id,
        "ready": ready,
        "outside": outside,
        "history": {"hold": history_hold},
        "medical_hold": None,
        "returned": False,
        "state": "intake",
        "adoptions": [{"receipt": receipt, "fee_cents": fee_cents}],
        "refunds": [],
    }


def adopt(case, receipt):
    return False


def return_to_shelter(case):
    return False
