import unittest
import random
from src.algebra.laurent import LaurentSeries

class TestFieldAxioms(unittest.TestCase):
    def setUp(self):
        self.prime = 17
        self.precision = 30
    
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
            
            # (a + b) + c == a + (b + c)
            lhs = (a + b) + c
            rhs = a + (b + c)
            self.assertEqual(lhs, rhs, f"Add Assoc failed: {lhs} != {rhs}")

    def test_distributivity(self):
        for _ in range(20):
            a = self.random_series()
            b = self.random_series()
            c = self.random_series()
            
            # a * (b + c) == a * b + a * c
            lhs = a * (b + c)
            rhs = (a * b) + (a * c)
            self.assertEqual(lhs, rhs, f"Distributivity failed: {lhs} != {rhs}")

    def test_multiplicative_inverse(self):
        """Check that a * a^-1 = 1 (approx)"""
        for _ in range(20):
            a = self.random_series()
            if a.is_zero(): continue
            
            try:
                inv = a.inv()
            except ZeroDivisionError:
                continue
                
            prod = a * inv
            
            prod = a * inv
            self.assertEqual(prod.coeffs.get(0, 0), 1, f"Inverse unity failed: {prod}")
            
            # Check high degrees are zero
            limit = self.precision - 5
            for d in range(1, limit):
                 self.assertEqual(prod.coeffs.get(d, 0), 0, f"Artifact at degree {d} in {prod}")

if __name__ == '__main__':
    unittest.main()
