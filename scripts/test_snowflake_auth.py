#!/usr/bin/env python3
"""Tests for how the refresh picks its Snowflake credential.

Run: python scripts/test_snowflake_auth.py

Worth testing despite being small: the service user is TYPE=SERVICE and
rejects password logins, so getting this wrong takes the whole daily refresh
down, and it only fails in CI where the real secret lives. Every case here is
one that has actually bitten or nearly bitten us — escaped newlines from
Railway, a PEM pasted into the base64 variable, a blank secret reading as
"configured".

No Snowflake account and no network: the connector is never called. These
assert on the kwargs the refresh would hand it.
"""

import base64
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from refresh_data import snowflake_auth, _der_from_pem  # noqa: E402

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# Generated per-run rather than checked in: a test fixture that looks like a
# real private key is exactly the thing a secret scanner should flag, and
# committing one trains people to ignore that alarm.
_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PEM = _KEY.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
).decode()
EXPECTED_DER = _KEY.private_bytes(
    encoding=serialization.Encoding.DER,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)


class KeyPairAuth(unittest.TestCase):
    def test_pem_is_converted_to_der(self):
        auth = snowflake_auth({"SNOWFLAKE_PRIVATE_KEY": PEM})
        self.assertEqual(auth, {"private_key": EXPECTED_DER})

    def test_escaped_newlines_are_accepted(self):
        # Railway can deliver a multi-line variable with literal \n sequences.
        auth = snowflake_auth({"SNOWFLAKE_PRIVATE_KEY": PEM.replace("\n", "\\n")})
        self.assertEqual(auth, {"private_key": EXPECTED_DER})

    def test_surrounding_whitespace_is_ignored(self):
        auth = snowflake_auth({"SNOWFLAKE_PRIVATE_KEY": "\n  " + PEM + "  \n"})
        self.assertEqual(auth, {"private_key": EXPECTED_DER})

    def test_key_wins_over_password(self):
        # The whole point: when a key is present no password may be sent, or
        # the service user rejects the login.
        auth = snowflake_auth({"SNOWFLAKE_PRIVATE_KEY": PEM,
                               "SNOWFLAKE_PASSWORD": "leftover"})
        self.assertNotIn("password", auth)
        self.assertIn("private_key", auth)


class Base64Variable(unittest.TestCase):
    def test_base64_pem_still_works(self):
        auth = snowflake_auth({
            "SNOWFLAKE_PRIVATE_KEY_B64": base64.b64encode(PEM.encode()).decode()})
        self.assertEqual(auth, {"private_key": EXPECTED_DER})

    def test_raw_pem_in_the_b64_variable_is_tolerated(self):
        auth = snowflake_auth({"SNOWFLAKE_PRIVATE_KEY_B64": PEM})
        self.assertEqual(auth, {"private_key": EXPECTED_DER})

    def test_pem_variable_takes_precedence(self):
        auth = snowflake_auth({
            "SNOWFLAKE_PRIVATE_KEY": PEM,
            "SNOWFLAKE_PRIVATE_KEY_B64": "not-a-key"})
        self.assertEqual(auth, {"private_key": EXPECTED_DER})


class PasswordFallback(unittest.TestCase):
    def test_password_used_when_no_key(self):
        self.assertEqual(snowflake_auth({"SNOWFLAKE_PASSWORD": "pw"}),
                         {"password": "pw"})

    def test_blank_key_falls_through_to_password(self):
        # An unset GitHub secret arrives as "", not as a missing variable.
        auth = snowflake_auth({"SNOWFLAKE_PRIVATE_KEY": "",
                               "SNOWFLAKE_PRIVATE_KEY_B64": "  ",
                               "SNOWFLAKE_PASSWORD": "pw"})
        self.assertEqual(auth, {"password": "pw"})


class Errors(unittest.TestCase):
    def test_key_without_begin_header_names_the_variable(self):
        with self.assertRaises(ValueError) as e:
            snowflake_auth({"SNOWFLAKE_PRIVATE_KEY": "AAAA1234notapem"})
        self.assertIn("SNOWFLAKE_PRIVATE_KEY", str(e.exception))

    def test_no_credential_at_all_explains_what_to_set(self):
        with self.assertRaises(RuntimeError) as e:
            snowflake_auth({})
        self.assertIn("SNOWFLAKE_PRIVATE_KEY", str(e.exception))

    def test_error_never_contains_the_secret(self):
        secret = "-----BEGIN RSA PRIVATE KEY-----\nSUPERSECRETMATERIAL\n"
        with self.assertRaises(Exception) as e:
            snowflake_auth({"SNOWFLAKE_PRIVATE_KEY": secret})
        self.assertNotIn("SUPERSECRETMATERIAL", str(e.exception))

    def test_length_reported_not_content(self):
        with self.assertRaises(ValueError) as e:
            _der_from_pem("abcdef", "SNOWFLAKE_PRIVATE_KEY")
        self.assertIn("6 characters", str(e.exception))
        self.assertNotIn("abcdef", str(e.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
