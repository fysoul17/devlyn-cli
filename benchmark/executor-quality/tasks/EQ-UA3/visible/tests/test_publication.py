import unittest

from publication import DraftError, slug_is_taken, validate_draft


class PublicationTests(unittest.TestCase):
    def test_validates_draft(self) -> None:
        draft = {"title": "Release notes", "slug": "release-notes"}

        self.assertEqual(validate_draft(draft), draft)

    def test_rejects_bad_slug(self) -> None:
        with self.assertRaisesRegex(DraftError, "URL-safe"):
            validate_draft({"title": "Release notes", "slug": "Release Notes"})

    def test_reports_occupied_slug(self) -> None:
        destinations = {"news": ["release-notes"]}
        self.assertTrue(slug_is_taken(destinations, "news", "release-notes"))


if __name__ == "__main__":
    unittest.main()
