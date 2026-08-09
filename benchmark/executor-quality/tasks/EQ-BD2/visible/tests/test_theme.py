import unittest

from theme import Theme, ThemeError


class ThemeTests(unittest.TestCase):
    def test_sets_a_known_color_token(self):
        theme = Theme({"accent": "#112233"})
        theme.set_token("accent", "#AABBCC")
        self.assertEqual(theme.tokens, {"accent": "#aabbcc"})
        self.assertEqual(theme.version, 1)

    def test_rejects_an_unknown_token(self):
        theme = Theme({"accent": "#112233"})
        with self.assertRaises(ThemeError):
            theme.set_token("background", "#ffffff")


if __name__ == "__main__":
    unittest.main()
