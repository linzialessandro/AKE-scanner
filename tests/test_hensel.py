import unittest

import _pathsetup  # noqa: F401
from ake_scanner.algebra.laurent import LaurentSeries
from ake_scanner.algebra.hensel import (
    sqrt_series,
    nth_root,
    is_nth_power,
    hensel_lift,
    has_root_via_hensel,
    is_quadratic_residue,
    sqrt_mod_p,
)
from ake_scanner.logic.scanner import scan_primes, FieldFactory


class TestFiniteFieldHelpers(unittest.TestCase):
    def test_quadratic_residues(self):
        self.assertTrue(is_quadratic_residue(0, 7))
        self.assertTrue(is_quadratic_residue(1, 7))
        self.assertTrue(is_quadratic_residue(2, 7))  # 3^2=9=2
        self.assertFalse(is_quadratic_residue(3, 7))

    def test_sqrt_mod_p(self):
        self.assertEqual(sqrt_mod_p(0, 11), 0)
        r = sqrt_mod_p(5, 11)
        self.assertIsNotNone(r)
        self.assertEqual((r * r) % 11, 5)
        self.assertIsNone(sqrt_mod_p(2, 11))


class TestSqrtSeries(unittest.TestCase):
    def test_one_plus_t_odd_prime(self):
        s = LaurentSeries({0: 1, 1: 1}, prime=5, precision=20)
        root = sqrt_series(s)
        self.assertIsNotNone(root)
        diff = root * root - s
        self.assertTrue(diff.is_zero() or int(diff.valuation) > 15)

    def test_one_plus_t_char_2(self):
        s = LaurentSeries({0: 1, 1: 1}, prime=2, precision=20)
        self.assertIsNone(sqrt_series(s))  # odd degree term

    def test_square_in_char_2(self):
        # 1 + t^2 = (1+t)^2 in char 2
        s = LaurentSeries({0: 1, 2: 1}, prime=2, precision=20)
        root = sqrt_series(s)
        self.assertIsNotNone(root)
        self.assertEqual(root.coeffs.get(0), 1)
        self.assertEqual(root.coeffs.get(1), 1)

    def test_odd_valuation(self):
        t = LaurentSeries.t(5, 20)
        self.assertIsNone(sqrt_series(t))

    def test_non_residue_unit(self):
        # 3 is non-residue mod 7
        s = LaurentSeries({0: 3}, prime=7, precision=10)
        self.assertIsNone(sqrt_series(s))


class TestNthRoot(unittest.TestCase):
    def test_cube_root_one_plus_t(self):
        s = LaurentSeries({0: 1, 1: 1}, prime=5, precision=20)
        root = nth_root(s, 3)
        self.assertIsNotNone(root)
        diff = (root ** 3) - s
        self.assertTrue(diff.is_zero() or int(diff.valuation) > 15)

    def test_cube_root_fails_p_equals_3(self):
        s = LaurentSeries({0: 1, 1: 1}, prime=3, precision=20)
        self.assertIsNone(nth_root(s, 3))

    def test_is_nth_power(self):
        s = LaurentSeries({0: 1, 1: 1}, prime=11, precision=15)
        self.assertTrue(is_nth_power(s, 2))
        self.assertFalse(is_nth_power(LaurentSeries.t(11, 15), 2))


class TestHenselLift(unittest.TestCase):
    def test_lift_square_equation(self):
        # f(x) = x^2 - (1+t)
        p, prec = 5, 20
        one_plus_t = LaurentSeries({0: 1, 1: 1}, p, prec)
        coeffs = [
            -one_plus_t,
            LaurentSeries.zero(p, prec),
            LaurentSeries.one(p, prec),
        ]
        # residue root of x^2 - 1 = 0: x=1 or 4
        x0 = LaurentSeries.constant(1, p, prec)
        root = hensel_lift(coeffs, x0, prec)
        self.assertIsNotNone(root)
        diff = root * root - one_plus_t
        self.assertTrue(diff.is_zero() or int(diff.valuation) > 15)

    def test_has_root_via_hensel_x2_minus_one(self):
        # x^2 - 1 has roots for all p
        self.assertTrue(has_root_via_hensel([-1, 0, 1], prime=7, precision=10))

    def test_has_root_x2_plus_one(self):
        # x^2 + 1 = 0 iff p = 2 or p ≡ 1 mod 4
        self.assertTrue(has_root_via_hensel([1, 0, 1], prime=5, precision=10))
        self.assertFalse(has_root_via_hensel([1, 0, 1], prime=7, precision=10))


class TestConstructiveSentences(unittest.TestCase):
    def test_one_plus_t_square_scan(self):
        def pred(F: FieldFactory):
            return sqrt_series(F.constant(1) + F.t, F.precision) is not None

        results = scan_primes(pred, prime_limit=30, precision=20)
        self.assertNotIn(2, results["passed_primes"])
        self.assertIn(2, results["failed_primes"])
        for p in [3, 5, 7, 11, 13, 17, 19, 23, 29]:
            self.assertIn(p, results["passed_primes"], f"expected pass at p={p}")

    def test_one_plus_t_cube_scan(self):
        def pred(F: FieldFactory):
            return nth_root(F.constant(1) + F.t, 3, F.precision) is not None

        results = scan_primes(pred, prime_limit=20, precision=20)
        self.assertIn(3, results["failed_primes"])
        for p in [2, 5, 7, 11, 13, 17, 19]:
            self.assertIn(p, results["passed_primes"], f"expected pass at p={p}")


if __name__ == "__main__":
    unittest.main()
