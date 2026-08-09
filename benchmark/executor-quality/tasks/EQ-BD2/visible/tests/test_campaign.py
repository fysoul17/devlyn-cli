import unittest

from campaign import render_banner
from theme import Theme


class CampaignTests(unittest.TestCase):
    def test_renders_current_theme_tokens(self):
        theme = Theme({"accent": "#112233", "background": "#ffffff"})
        self.assertEqual(
            render_banner(theme),
            '<section style="background:#ffffff;color:#112233">Launch</section>',
        )


if __name__ == "__main__":
    unittest.main()
