import unittest
import random

import _pathsetup  # noqa: F401
from ake_scanner.algebra.laurent import LaurentSeries


class TestFieldAxioms(unittest.TestCase):
    def setUp(self):
        self.prime = 17
        self.precision = 30
        random.seed(42)

    def random_series(self, min_deg=-5, max_deg=10, density=0.5):
        coeffs = {}
        for d in range(min_deg, max_deg + 1):
            if random.random() < density:
                coeffs[d] = random.randint(0, self.prime - 1)
        return LaurentSeries(coeffs, self.prime, self.precision)

    def test_associativity_addition(self):
        for _ in range(20):
            a = self.random_series()
            b = self.random_series()
            c = self.random_series()

            lhs = (a + b) + c
            rhs = a + (b + c)
            self.assertEqual(lhs, rhs, f"Add Assoc failed: {lhs} != {rhs}")

    def test_distributivity(self):
        for _ in range(20):
            a = self.random_series()
            b = self.random_series()
            c = self.random_series()

            lhs = a * (b + c)
            rhs = (a * b) + (a * c)
            self.assertEqual(lhs, rhs, f"Distributivity failed: {lhs} != {rhs}")

    def test_multiplicative_inverse(self):
        """Check a * a^-1 = 1 inside the absolute-precision safe window."""
        for _ in range(40):
            a = self.random_series(min_deg=-8, max_deg=12)
            if a.is_zero():
                continue

            inv = a.inv()
            prod = a * inv
            safe = a.inverse_product_safe_degree()

            self.assertEqual(
                prod.coeffs.get(0, 0),
                1,
                f"Inverse unity failed: a={a}, prod={prod}",
            )
            for d in range(1, safe + 1):
                self.assertEqual(
                    prod.coeffs.get(d, 0),
                    0,
                    f"Artifact at degree {d} in {prod} (a={a}, safe={safe})",
                )

    def test_multiplicative_inverse_nonnegative_val(self):
        """Nonnegative valuation: full absolute precision cancellation."""
        for _ in range(30):
            a = self.random_series(min_deg=0, max_deg=12)
            if a.is_zero():
                continue
            prod = a * a.inv()
            self.assertEqual(prod.coeffs.get(0, 0), 1)
            for d in range(1, self.precision + 1):
                self.assertEqual(
                    prod.coeffs.get(d, 0),
                    0,
                    f"Artifact at degree {d} in {prod} (a={a})",
                )

    def test_division_roundtrip(self):
        for _ in range(20):
            a = self.random_series(min_deg=0, max_deg=8)
            b = self.random_series(min_deg=0, max_deg=8)
            if b.is_zero():
                continue
            q = a / b
            recovered = q * b
            # (a/b)*b recovers a below the safe product window of b.inv()
            safe = b.inverse_product_safe_degree()
            for d in range(0, min(safe, self.precision - 2) + 1):
                self.assertEqual(
                    recovered.coeffs.get(d, 0),
                    a.coeffs.get(d, 0) % self.prime,
                    f"Roundtrip failed at deg {d}: a={a}, recovered={recovered}",
                )


if __name__ == "__main__":
    unittest.main()
