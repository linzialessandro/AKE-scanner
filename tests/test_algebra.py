import unittest

import _pathsetup  # noqa: F401
from ake_scanner.algebra.laurent import LaurentSeries


class TestLaurentSeries(unittest.TestCase):
    def test_creation(self):
        ls = LaurentSeries({0: 1, 1: 2, 2: 0}, prime=5, precision=10)
        self.assertEqual(ls.coeffs[0], 1)
        self.assertEqual(ls.coeffs[1], 2)
        self.assertNotIn(2, ls.coeffs)
        self.assertEqual(ls.valuation, 0)

    def test_addition(self):
        # (1 + t) + (2 + 3t) = 3 + 4t
        l1 = LaurentSeries({0: 1, 1: 1}, prime=5)
        l2 = LaurentSeries({0: 2, 1: 3}, prime=5)
        res = l1 + l2
        self.assertEqual(res.coeffs[0], 3)
        self.assertEqual(res.coeffs[1], 4)

    def test_addition_modulo(self):
        l1 = LaurentSeries({0: 2}, prime=5)
        l2 = LaurentSeries({0: 3}, prime=5)
        res = l1 + l2
        self.assertTrue(res.is_zero())

    def test_multiplication(self):
        l1 = LaurentSeries({0: 1, 1: 1}, prime=5)
        l2 = LaurentSeries({0: 1, 1: 4}, prime=5)
        res = l1 * l2
        self.assertEqual(res.coeffs[0], 1)
        self.assertNotIn(1, res.coeffs)
        self.assertEqual(res.coeffs[2], 4)

    def test_valuation(self):
        ls = LaurentSeries({2: 3}, prime=5)
        self.assertEqual(ls.valuation, 2)

        ls_zero = LaurentSeries({}, prime=5)
        self.assertEqual(ls_zero.valuation, float("inf"))

    def test_inversion_unit(self):
        # (1 + t)^-1 = 1 - t + t^2 - t^3 ...
        ls = LaurentSeries({0: 1, 1: 1}, prime=5, precision=5)
        inv = ls.inv()

        prod = ls * inv
        self.assertEqual(prod.coeffs.get(0), 1)
        self.assertNotIn(1, prod.coeffs)
        self.assertNotIn(2, prod.coeffs)

    def test_inversion_shifted(self):
        t = LaurentSeries({1: 1}, prime=5)
        t_inv = t.inv()

        self.assertEqual(t_inv.valuation, -1)
        self.assertEqual(t_inv.coeffs[-1], 1)

        prod = t * t_inv
        self.assertEqual(prod.coeffs[0], 1)
        self.assertEqual(len(prod.coeffs), 1)

    def test_inversion_negative_valuation_safe_window(self):
        """With absolute truncation, cancel only up to precision + min(0, val)."""
        p, prec = 7, 5
        a = LaurentSeries({-2: 3, 0: 1}, p, prec)
        prod = a * a.inv()
        safe = a.inverse_product_safe_degree()  # 5 + (-2) = 3
        self.assertEqual(safe, 3)
        self.assertEqual(prod.coeffs.get(0, 0), 1)
        for d in range(1, safe + 1):
            self.assertEqual(
                prod.coeffs.get(d, 0),
                0,
                f"Residual term at degree {d}: {prod}",
            )

    def test_inversion_high_positive_valuation(self):
        p, prec = 7, 10
        s = LaurentSeries({3: 1, 4: 1}, p, prec)
        prod = s * s.inv()
        self.assertEqual(prod.coeffs.get(0, 0), 1)
        for d in range(1, prec + 1):
            self.assertEqual(prod.coeffs.get(d, 0), 0, f"Residual at {d}: {prod}")

    def test_precision_min_on_ops(self):
        x = LaurentSeries({0: 1, 1: 1, 2: 1}, prime=7, precision=3)
        y = LaurentSeries({0: 1, 1: 1, 5: 1}, prime=7, precision=10)
        res = x * y
        self.assertEqual(res.precision, 3)
        # y's t^5 term must not contribute beyond prec 3
        self.assertNotIn(5, res.coeffs)
        self.assertNotIn(6, res.coeffs)

    def test_leading_and_unit_part(self):
        s = LaurentSeries({2: 3, 3: 4}, prime=5, precision=10)
        self.assertEqual(s.leading_coefficient(), 3)
        u = s.unit_part()
        self.assertEqual(u.valuation, 0)
        self.assertEqual(u.coeffs[0], 3)
        self.assertEqual(u.coeffs[1], 4)
        self.assertEqual(s.residue(), 3)

    def test_shift(self):
        s = LaurentSeries({0: 1, 1: 2}, prime=5, precision=10)
        shifted = s.shift(3)
        self.assertEqual(shifted.coeffs, {3: 1, 4: 2})
        self.assertEqual(s.shift(-1).valuation, -1)

    def test_division(self):
        a = LaurentSeries({0: 1, 1: 1}, prime=5, precision=8)
        b = LaurentSeries({0: 2}, prime=5, precision=8)
        q = a / b
        # (1+t)/2 = 3(1+t) mod 5
        self.assertEqual(q.coeffs[0], 3)
        self.assertEqual(q.coeffs[1], 3)
        prod = q * b
        self.assertEqual(prod.coeffs.get(0), 1)
        self.assertEqual(prod.coeffs.get(1), 1)

    def test_power(self):
        t = LaurentSeries.t(5, 10)
        self.assertEqual((t ** 3).coeffs, {3: 1})
        self.assertEqual((t ** 0).coeffs, {0: 1})
        one_plus_t = LaurentSeries({0: 1, 1: 1}, prime=5, precision=10)
        sq = one_plus_t ** 2
        self.assertEqual(sq.coeffs[0], 1)
        self.assertEqual(sq.coeffs[1], 2)
        self.assertEqual(sq.coeffs[2], 1)

        inv_pow = one_plus_t ** -1
        prod = one_plus_t * inv_pow
        self.assertEqual(prod.coeffs.get(0), 1)
        for d in range(1, 11):
            self.assertEqual(prod.coeffs.get(d, 0), 0)

    def test_bool_and_zero_one(self):
        z = LaurentSeries.zero(5, 10)
        o = LaurentSeries.one(5, 10)
        self.assertFalse(z)
        self.assertTrue(o)
        self.assertTrue(z.is_zero())


if __name__ == "__main__":
    unittest.main()
