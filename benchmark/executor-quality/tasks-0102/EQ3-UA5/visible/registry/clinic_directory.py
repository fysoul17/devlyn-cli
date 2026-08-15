"""Clinic contact lookup."""


def coordinator(site):
    return {"north": "Ari", "south": "Jo"}.get(site, "Desk")
