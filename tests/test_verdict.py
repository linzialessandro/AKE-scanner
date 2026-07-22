import unittest

import _pathsetup  # noqa: F401
from ake_scanner.logic.diagnose import diagnose_residue_square, diagnose_x_n_equals
from ake_scanner.logic.scanner import FieldFactory, scan_primes
from ake_scanner.logic.verdict import (
    CODE_NONSQUARE_RESIDUE,
    CODE_ODD_VALUATION,
    CODE_P_DIVIDES_N,
    CODE_WITNESS,
)
from ake_scanner.algebra.laurent import LaurentSeries


class TestDiagnose(unittest.TestCase):
    def test_odd_valuation_obstruction(self):
        t = LaurentSeries.t(5, 20)
        v = diagnose_x_n_equals(t, 2, 20)
        self.assertFalse(v.holds)
        self.assertEqual(v.code, CODE_ODD_VALUATION)

    def test_square_of_one_plus_t_at_5(self):
        F = FieldFactory(5, 20)
        v = diagnose_x_n_equals(F.constant(1) + F.t, 2, 20)
        self.assertTrue(v.holds)
        self.assertEqual(v.code, CODE_WITNESS)
        self.assertIsNotNone(v.witness)
        self.assertEqual(v.witness["kind"], "laurent")

    def test_p_divides_n_cube_at_3(self):
        F = FieldFactory(3, 20)
        v = diagnose_x_n_equals(F.constant(1) + F.t, 3, 20)
        self.assertFalse(v.holds)
        self.assertEqual(v.code, CODE_P_DIVIDES_N)

    def test_minus_one_mod_4(self):
        ok7 = diagnose_residue_square(-1, 5)  # 5 ≡ 1 mod 4
        self.assertTrue(ok7.holds)
        bad = diagnose_residue_square(-1, 7)  # 7 ≡ 3 mod 4
        self.assertFalse(bad.holds)
        self.assertEqual(bad.code, CODE_NONSQUARE_RESIDUE)


class TestScanExplain(unittest.TestCase):
    def test_verdict_predicate_fills_explanations(self):
        def pred(F):
            return diagnose_x_n_equals(F.constant(1) + F.t, 2, F.precision)

        r = scan_primes(pred, prime_limit=11, precision=16)
        self.assertIn(2, r["failed_primes"])
        self.assertIn(2, r["explanations"])
        self.assertFalse(r["explanations"][2]["holds"])
        # a larger prime should pass with witness
        passed = r["passed_primes"]
        self.assertTrue(passed)
        p = passed[0]
        self.assertTrue(r["explanations"][p]["holds"])
        self.assertEqual(r["explanations"][p]["code"], CODE_WITNESS)

    def test_bool_predicate_explain_flag(self):
        def pred(F):
            return F.prime != 2

        r = scan_primes(pred, prime_limit=7, explain=True)
        self.assertEqual(set(r["explanations"].keys()), set(r["primes_scanned"]))


if __name__ == "__main__":
    unittest.main()
