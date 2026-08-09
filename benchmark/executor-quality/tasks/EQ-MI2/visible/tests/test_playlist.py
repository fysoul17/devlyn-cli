from __future__ import annotations

import unittest

import playlist


class PlaylistTests(unittest.TestCase):
    def setUp(self) -> None:
        playlist.clear()

    def test_create_and_append_keep_input_order(self) -> None:
        playlist.create_playlist("drive", ["intro", "middle"])
        playlist.append_track("drive", "finale")

        self.assertEqual(
            playlist.get_tracks("drive"),
            ["intro", "middle", "finale"],
        )

    def test_get_tracks_returns_a_copy(self) -> None:
        playlist.create_playlist("focus", ["alpha"])

        returned = playlist.get_tracks("focus")
        returned.append("beta")

        self.assertEqual(playlist.get_tracks("focus"), ["alpha"])


if __name__ == "__main__":
    unittest.main()
