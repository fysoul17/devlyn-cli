ALIASES = {
    "north-pump": "M-17",
    "school-wing": "M-24",
}


def canonical_meter(label):
    return ALIASES.get(label, label)
