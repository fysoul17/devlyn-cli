"""Operational notes expressed as simple predicates."""


def requires_bonded_review(country_code):
    return country_code != "KR"


def has_required_documents(documents):
    return "invoice" in documents and "packing-list" in documents
