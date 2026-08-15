"""Published claim-rate reference."""


def band_name(amount):
    return "material" if amount >= 600 else "routine"
