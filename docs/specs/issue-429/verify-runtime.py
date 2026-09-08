"""Check issue 429 and preserve existing serializer behavior."""

import datetime as dt
import importlib
import sys
import unittest
from pathlib import Path

from freezegun import freeze_time

SOURCE = (Path.cwd() / "src").resolve()
sys.path.insert(0, str(SOURCE))
itsdangerous = importlib.import_module("itsdangerous")
assert Path(itsdangerous.__file__).resolve().is_relative_to(SOURCE)


class SerializerContract(unittest.TestCase):
    def test_untimed_rejects_max_age(self):
        serializer = itsdangerous.URLSafeSerializer("SECRET")
        signed = serializer.dumps("value")
        with self.assertRaises(TypeError):
            serializer.loads(signed, max_age=-1)

    def test_untimed_roundtrip_salt_and_unsafe(self):
        serializer = itsdangerous.URLSafeSerializer("SECRET")
        value = {"id": 42}
        signed = serializer.dumps(value)
        self.assertEqual(serializer.loads(signed), value)
        self.assertEqual(serializer.loads(signed.encode()), value)
        salted = serializer.dumps(value, salt="other")
        self.assertEqual(serializer.loads(salted, salt="other"), value)
        with self.assertRaises(itsdangerous.BadSignature):
            serializer.loads(salted)
        self.assertEqual(serializer.loads_unsafe(salted, salt="other"), (True, value))
        self.assertEqual(serializer.loads_unsafe(salted), (False, value))

    def test_timed_expiration_timestamp_salt_and_unsafe(self):
        serializer = itsdangerous.URLSafeTimedSerializer("SECRET")
        value = "value"
        timestamp = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
        with freeze_time(timestamp) as clock:
            signed = serializer.dumps(value, salt="other")
            self.assertEqual(serializer.loads(signed, salt="other"), value)
            self.assertEqual(serializer.loads(signed, max_age=10, salt="other"), value)
            self.assertEqual(
                serializer.loads(
                    signed, max_age=10, return_timestamp=True, salt="other"
                ),
                (value, timestamp),
            )
            self.assertEqual(
                serializer.loads_unsafe(signed, max_age=10, salt="other"),
                (True, value),
            )
            clock.tick(11)
            with self.assertRaises(itsdangerous.SignatureExpired):
                serializer.loads(signed, max_age=10, salt="other")
            self.assertEqual(
                serializer.loads_unsafe(signed, max_age=10, salt="other"),
                (False, value),
            )
            self.assertEqual(serializer.loads(signed, salt="other"), value)


if __name__ == "__main__":
    unittest.main(verbosity=2)
