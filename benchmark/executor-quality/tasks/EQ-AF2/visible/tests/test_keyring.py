from __future__ import annotations

import unittest

from keyring import Keyring


class KeyringTests(unittest.TestCase):
    def test_adds_ciphertext_under_the_active_key(self) -> None:
        keyring = Keyring("key-a")

        keyring.add("mail", "cipher-a")

        self.assertEqual(keyring.active_key, "key-a")
        self.assertEqual(keyring.secrets, {"mail": "cipher-a"})
        self.assertEqual(keyring.completed_rotations, 0)

    def test_rejects_a_duplicate_name(self) -> None:
        keyring = Keyring("key-a")
        keyring.add("mail", "cipher-a")

        with self.assertRaisesRegex(ValueError, "secret already exists"):
            keyring.add("mail", "cipher-b")

        self.assertEqual(keyring.secrets, {"mail": "cipher-a"})


if __name__ == "__main__":
    unittest.main()
