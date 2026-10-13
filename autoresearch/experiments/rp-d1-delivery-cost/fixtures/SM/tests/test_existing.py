from slugtools import slugify


def test_existing_slug():
    assert slugify('already-a-slug-42') == 'already-a-slug-42'
