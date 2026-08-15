"""Reference rates used by the assessment desk."""


TARIFF_DESCRIPTIONS = {
    "0101": "Live horses",
    "0201": "Beef, fresh or chilled",
    "0401": "Milk and cream",
}


def known_heading(code):
    return code in TARIFF_DESCRIPTIONS
