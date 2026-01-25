import unittest
from src.logic.scanner import is_prime, generate_primes, scan_primes, FieldFactory

class TestScanner(unittest.TestCase):
    def test_is_prime(self):
        self.assertTrue(is_prime(2))
        self.assertTrue(is_prime(3))
        self.assertTrue(is_prime(5))
        self.assertTrue(is_prime(17)) 
        self.assertFalse(is_prime(1))
        self.assertFalse(is_prime(4))
        self.assertFalse(is_prime(15))

    def test_generate_primes(self):
        primes = list(generate_primes(10))
        self.assertEqual(primes, [2, 3, 5, 7])

    def test_field_factory(self):
        ff = FieldFactory(prime=7, precision=10)
        t = ff.t
        self.assertEqual(t.prime, 7)
        self.assertEqual(t.valuation, 1)

    def test_scan_primes_trivial(self):
        # Predicate that is always true
        def always_true(F):
            return True
        
        results = scan_primes(always_true, prime_limit=5)
        # Primes: 2, 3, 5
        self.assertEqual(results['verified_count'], 3)
        self.assertEqual(results['passed_primes'], [2, 3, 5])
        self.assertEqual(results['failed_primes'], [])

    def test_scan_primes_conditional(self):
        # True only for p=2
        def only_two(F):
            return F.prime == 2
            
        results = scan_primes(only_two, prime_limit=5)
        self.assertEqual(results['verified_count'], 1)
        self.assertEqual(results['passed_primes'], [2])
        self.assertEqual(results['failed_primes'], [3, 5])

if __name__ == '__main__':
    unittest.main()
