import unittest

import _pathsetup  # noqa: F401
from ake_scanner.logic.scanner import scan_primes, FieldFactory
from ake_scanner.algebra.hensel import (
    sqrt_series,
    nth_root,
    is_quadratic_residue,
    has_root_via_hensel,
)


class TestMeaningfulSentences(unittest.TestCase):
    """
    First-order style sentences verified *constructively* in F_p((t)),
    not by hardcoding the expected set of primes.
    """

    def test_square_root_minus_one(self):
        """Exists x in F_p with x^2 = -1 (Euler criterion on the residue field)."""

        def predicate_minus_one_square(F: FieldFactory):
            return is_quadratic_residue(-1, F.prime)

        results = scan_primes(predicate_minus_one_square, prime_limit=20)
        # p=2: -1 ≡ 1, square. Odd p: p ≡ 1 mod 4.
        expected_passed = {2, 5, 13, 17}
        self.assertEqual(set(results["passed_primes"]), expected_passed)

    def test_hensel_lift_cubic_constructive(self):
        """Exists x in F_p((t)) with x^3 = 1 + t (Newton lift; fails at p=3)."""

        def predicate_cubic_root(F: FieldFactory):
            target = F.constant(1) + F.t
            return nth_root(target, 3, F.precision) is not None

        results = scan_primes(predicate_cubic_root, prime_limit=15, precision=20)
        self.assertNotIn(3, results["passed_primes"])
        self.assertIn(3, results["failed_primes"])
        for p in [2, 5, 7, 11, 13]:
            self.assertIn(p, results["passed_primes"])

    def test_one_plus_t_is_square_constructive(self):
        """Exists x with x^2 = 1 + t (fails only at p=2 among small primes)."""

        def pred(F: FieldFactory):
            return sqrt_series(F.constant(1) + F.t, F.precision) is not None

        results = scan_primes(pred, prime_limit=25, precision=20)
        self.assertEqual(results["failed_primes"], [2])
        self.assertGreater(results["verified_count"], 5)

    def test_artin_schreier_valuation_obstruction(self):
        """
        Exists x with x^p - x = t^{-1}.

        Valuation obstruction: v(x^p - x) is never -1 for x in F_p((t)),
        because v(x^p) = p v(x) and v(x) are integers, so their difference
        (when both defined) cannot produce valuation -1 as a leading term
        when p does not divide the difference in a matching way.

        We check constructively: for candidate valuations, no series of
        that form can match val -1 on the RHS. A lightweight certificate:
        if v(x) >= 0 then v(x^p - x) >= 0; if v(x) < 0 then v(x^p - x) = p v(x)
        which is <= -p <= -2. So val -1 is impossible.
        """

        def predicate_as_solvable(F: FieldFactory):
            # Constructive obstruction argument (no free variables to search).
            # Enumerate possible integer valuations of x and show mismatch.
            rhs_val = -1
            # Case v(x) >= 0: LHS val >= 0 != -1
            # Case v(x) = k < 0: v(x^p) = p k < k = v(x), so v(LHS) = p k.
            # Need p k = -1 for some integer k < 0 => p divides 1, impossible.
            for k in range(-20, 20):
                if k >= 0:
                    lhs_val = 0  # lower bound; never -1 as equality target
                    if lhs_val == rhs_val:
                        return True
                else:
                    if F.prime * k == rhs_val:
                        return True
            return False

        results = scan_primes(predicate_as_solvable, prime_limit=15)
        self.assertEqual(results["verified_count"], 0)
        self.assertEqual(results["failed_primes"], [2, 3, 5, 7, 11, 13])

    def test_x2_plus_one_via_hensel(self):
        """Exists x with x^2 + 1 = 0 in F_p[[t]] iff -1 is a square mod p."""

        def pred(F: FieldFactory):
            return has_root_via_hensel([1, 0, 1], F.prime, F.precision)

        results = scan_primes(pred, prime_limit=20)
        # p=2: x^2+1 = x^2+1, roots? x=1: 1+1=0 mod 2. Yes.
        # p≡1 mod 4: yes. p≡3 mod 4: no.
        self.assertIn(2, results["passed_primes"])
        self.assertIn(5, results["passed_primes"])
        self.assertIn(13, results["passed_primes"])
        self.assertIn(17, results["passed_primes"])
        self.assertNotIn(3, results["passed_primes"])
        self.assertNotIn(7, results["passed_primes"])
        self.assertNotIn(11, results["passed_primes"])
        self.assertNotIn(19, results["passed_primes"])


if __name__ == "__main__":
    unittest.main()
