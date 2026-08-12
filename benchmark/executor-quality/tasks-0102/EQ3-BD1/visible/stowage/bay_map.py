"""Static berth labels for the small terminal fixture."""


BAYS = {"A": "forward", "B": "midship", "C": "aft"}


def label_for(index):
    return BAYS["ABC"[index % 3]]
