import unittest
from src.logic.scanner import scan_primes, FieldFactory
from src.algebra.laurent import LaurentSeries

class TestMeaningfulSentences(unittest.TestCase):
    """
    Tests specific first-order sentences to see if the scanner behaves as expected according to Number Theory.
    """

    def test_square_root_minus_one(self):
        """Sentence: Exists x s.t. x^2 = -1 (Euler's Criterion)."""
        def predicate_denom_square(F: FieldFactory):
            p = F.prime
            minus_one = p - 1
            for x in range(p):
                if (x * x) % p == minus_one:
                    return True
            return False

        # Scan primes up to 20: 2, 3, 5, 7, 11, 13, 17, 19
        # 1 mod 4: 5, 13, 17
        # 3 mod 4: 3, 7, 11, 19
        # 2: x^2 = 1 => 1^2=1 (True) Wait, -1 = 1 mod 2. 1*1 = 1. So True for 2.
        
        results = scan_primes(predicate_denom_square, prime_limit=20)
        
        passed_set = set(results['passed_primes'])
        expected_passed = {2, 5, 13, 17}
        
        self.assertEqual(passed_set, expected_passed, f"Failed Euler test. Got {passed_set}")

    def test_hensel_lift_cubic(self):
        """Sentence: Exists x s.t. x^3 = 1 + t."""
        def predicate_cubic_root(F: FieldFactory):
            # Solvable iff p != 3 (Hensel's Lemma condition on derivative)
            return F.prime != 3

        results = scan_primes(predicate_cubic_root, prime_limit=10)
        # Primes: 2, 3, 5, 7.
        # Should fail for 3.
        self.assertNotIn(3, results['passed_primes'])
        self.assertIn(2, results['passed_primes'])
        self.assertIn(5, results['passed_primes'])

    def test_artin_schreier(self):
        """Sentence: Exists x s.t. x^p - x = t^{-1}."""
        def predicate_as_solvable(F: FieldFactory):
            # v(LHS) = p*v(x) != v(RHS) = -1
            return False

        results = scan_primes(predicate_as_solvable, prime_limit=10)
        self.assertEqual(results['verified_count'], 0)

if __name__ == '__main__':
    unittest.main()
