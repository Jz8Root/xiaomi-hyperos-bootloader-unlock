import unittest

import scan_lk


def make_lk(*parts):
    return b"\x00".join(parts) + b"\x00" * 512


class VerdictRegressionTest(unittest.TestCase):
    def test_full_requires_magic_and_seccfg(self):
        data = make_lk(
            scan_lk.RPMB_MAGIC,
            scan_lk.RSA_MODULUS_PREFIX,
            b"seccfg",
            b"oem lks",
        )

        result = scan_lk.scan_binary(data)

        self.assertEqual(result["verdict"]["compatibility"], "COMPATIBLE_FULL")

    def test_magic_without_seccfg_is_not_full(self):
        data = make_lk(
            scan_lk.RPMB_MAGIC,
            scan_lk.RSA_MODULUS_PREFIX,
            b"oem lks",
        )

        result = scan_lk.scan_binary(data)

        self.assertEqual(result["verdict"]["compatibility"], "MAYBE")
        self.assertIn("seccfg not detected", result["verdict"]["blockers"])

    def test_clean_path_b_candidate(self):
        data = make_lk(
            scan_lk.RSA_MODULUS_PREFIX,
            b"seccfg",
            b"oem lks",
        )

        result = scan_lk.scan_binary(data)

        self.assertEqual(result["verdict"]["compatibility"], "COMPATIBLE_SECCFG_ONLY")

    def test_mi_get_lock_state_without_magic_is_contradictory(self):
        data = make_lk(
            scan_lk.RSA_MODULUS_PREFIX,
            b"seccfg",
            b"oem lks",
            b"mi_get_lock_state",
        )

        result = scan_lk.scan_binary(data)

        self.assertEqual(result["verdict"]["compatibility"], "MAYBE")
        self.assertEqual(result["verdict"]["method"], "Live RPMB analysis required")

    def test_seccfg_string_alone_does_not_classify_path_b(self):
        result = scan_lk.scan_binary(make_lk(b"seccfg"))

        self.assertEqual(result["verdict"]["compatibility"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
