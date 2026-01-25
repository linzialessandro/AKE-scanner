import unittest
from src.algebra.laurent import LaurentSeries

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
        # 3t^2
        ls = LaurentSeries({2: 3}, prime=5)
        self.assertEqual(ls.valuation, 2)
        
        # 0
        ls_zero = LaurentSeries({}, prime=5)
        self.assertEqual(ls_zero.valuation, float('inf'))

    def test_inversion_unit(self):
        # (1 + t)^-1 = 1 - t + t^2 - t^3 ...
        # Mod 5: 1 + 4t + t^2 + 4t^3 ...
        ls = LaurentSeries({0: 1, 1: 1}, prime=5, precision=5)
        inv = ls.inv()
        
        # Check multiplication gives 1
        prod = ls * inv
        self.assertEqual(prod.coeffs.get(0), 1)
        # Higher terms should be 0 up to precision?
        # Due to cutoff, prod might have terms > precision or close to it.
        # Check low degree terms are 0
        self.assertNotIn(1, prod.coeffs)
        self.assertNotIn(2, prod.coeffs)

    def test_inversion_shifted(self):
        # t^-1
        # t has coeffs {1: 1}
        # inv should be { -1: 1 } ?? 
        # Wait, our current implementation likely expects standard Laurent series?
        # The prompt said "Field of formal Laurent series", which includes negative powers.
        # My implementation of `inv` handles shifting by valuation.
        
        t = LaurentSeries({1: 1}, prime=5) 
        t_inv = t.inv()
        
        # val(t) = 1. val(t_inv) should be -1.
        self.assertEqual(t_inv.valuation, -1)
        self.assertEqual(t_inv.coeffs[-1], 1)
        
        prod = t * t_inv
        self.assertEqual(prod.coeffs[0], 1)
        self.assertTrue(len(prod.coeffs) == 1) # Should just be 1

if __name__ == '__main__':
    unittest.main()
