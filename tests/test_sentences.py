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


class TestDemoPredicates(unittest.TestCase):
    """Asymptotic patterns for the non-trivial CLI demo predicates."""

    @classmethod
    def setUpClass(cls):
        import importlib.util
        import os

        path = os.path.join(
            os.path.dirname(__file__), "..", "examples", "demo_hensel.py"
        )
        path = os.path.abspath(path)
        spec = importlib.util.spec_from_file_location("demo_hensel_tests", path)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        cls.demo = mod

    def test_fifth_power_exceptional_at_5(self):
        r = scan_primes(
            self.demo.predicate_one_plus_t_is_fifth_power,
            prime_limit=25,
            precision=20,
        )
        self.assertEqual(r["asymptotic"]["pattern"], "eventually_true")
        self.assertEqual(r["failed_primes"], [5])
        self.assertEqual(r["holds_for_p_greater_than"], 5)

    def test_fourth_power_exceptional_at_2(self):
        r = scan_primes(
            self.demo.predicate_one_plus_two_t_is_fourth_power,
            prime_limit=25,
            precision=20,
        )
        self.assertEqual(r["asymptotic"]["pattern"], "eventually_true")
        self.assertEqual(r["failed_primes"], [2])

    def test_minus_one_mixed_mod_4(self):
        r = scan_primes(
            self.demo.predicate_minus_one_is_square, prime_limit=40
        )
        self.assertEqual(r["asymptotic"]["pattern"], "mixed")
        for p in r["passed_primes"]:
            self.assertTrue(p == 2 or p % 4 == 1)
        for p in r["failed_primes"]:
            self.assertEqual(p % 4, 3)

    def test_two_is_square_mixed_mod_8(self):
        r = scan_primes(self.demo.predicate_two_is_square, prime_limit=50)
        self.assertEqual(r["asymptotic"]["pattern"], "mixed")
        for p in r["passed_primes"]:
            self.assertTrue(p == 2 or p % 8 in (1, 7))
        for p in r["failed_primes"]:
            self.assertIn(p % 8, (3, 5))

    def test_cube_root_of_unity_mixed(self):
        r = scan_primes(
            self.demo.predicate_primitive_cube_root_of_unity, prime_limit=40
        )
        self.assertEqual(r["asymptotic"]["pattern"], "mixed")
        # p ≡ 1 (mod 3) should pass; p ≡ 2 (mod 3) should fail (p > 3)
        for p in r["passed_primes"]:
            if p > 3:
                self.assertEqual(p % 3, 1)
        for p in r["failed_primes"]:
            if p > 3:
                self.assertEqual(p % 3, 2)

    def test_x_cubed_minus_x_always_true(self):
        r = scan_primes(
            self.demo.predicate_x_cubed_minus_x_equals_t,
            prime_limit=30,
            precision=20,
        )
        self.assertEqual(r["asymptotic"]["pattern"], "always_true")
        self.assertEqual(r["failed_primes"], [])
        self.assertEqual(r["error_primes"], [])

    def test_artin_schreier_always_false(self):
        r = scan_primes(
            self.demo.predicate_artin_schreier_valuation_obstruction,
            prime_limit=25,
        )
        self.assertEqual(r["asymptotic"]["pattern"], "always_false")
        self.assertEqual(r["verified_count"], 0)

    def test_inverse_unit_square(self):
        r = scan_primes(
            self.demo.predicate_one_over_one_plus_t_is_square,
            prime_limit=25,
            precision=20,
        )
        self.assertEqual(r["asymptotic"]["pattern"], "eventually_true")
        self.assertEqual(r["failed_primes"], [2])

    def test_t_squared_always_true(self):
        r = scan_primes(
            self.demo.predicate_t_squared_is_square, prime_limit=20, precision=15
        )
        self.assertEqual(r["asymptotic"]["pattern"], "always_true")


class TestAdvancedSentences(unittest.TestCase):
    """Simultaneous systems, quantifier alternation, and (v, ac) demos."""

    @classmethod
    def setUpClass(cls):
        import importlib.util
        import os

        path = os.path.join(
            os.path.dirname(__file__), "..", "examples", "advanced_sentences.py"
        )
        path = os.path.abspath(path)
        spec = importlib.util.spec_from_file_location("advanced_sentences_tests", path)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        cls.adv = mod

    # --- simultaneous systems ---

    def test_sum_of_two_squares_t_mixed(self):
        r = scan_primes(
            self.adv.predicate_sum_of_two_squares_equals_t,
            prime_limit=45,
            precision=18,
        )
        self.assertEqual(r["asymptotic"]["pattern"], "mixed")
        # With constant y=1, needs -1 square ⇒ odd passes have p ≡ 1 (mod 4)
        for p in r["passed_primes"]:
            if p > 2:
                self.assertEqual(p % 4, 1)

    def test_sum_of_two_squares_one_plus_t(self):
        r = scan_primes(
            self.adv.predicate_sum_of_two_squares_equals_one_plus_t,
            prime_limit=25,
            precision=18,
        )
        self.assertEqual(r["asymptotic"]["pattern"], "eventually_true")
        self.assertEqual(r["failed_primes"], [2])

    def test_independent_simultaneous_squares(self):
        r = scan_primes(
            self.adv.predicate_independent_simultaneous_squares,
            prime_limit=25,
            precision=18,
        )
        self.assertEqual(r["asymptotic"]["pattern"], "eventually_true")
        self.assertIn(2, r["failed_primes"])

    def test_simultaneous_i_and_sqrt_mixed(self):
        r = scan_primes(
            self.adv.predicate_simultaneous_i_and_sqrt_one_plus_t,
            prime_limit=40,
            precision=18,
        )
        self.assertEqual(r["asymptotic"]["pattern"], "mixed")
        for p in r["passed_primes"]:
            self.assertTrue(p % 4 == 1)  # needs i; p=2 fails sqrt of 1+t

    def test_unit_circle_always_true(self):
        r = scan_primes(
            self.adv.predicate_pythagorean_unit_circle, prime_limit=25, precision=15
        )
        self.assertEqual(r["asymptotic"]["pattern"], "always_true")

    def test_product_and_sum_disc_5(self):
        r = scan_primes(
            self.adv.predicate_simultaneous_product_and_sum, prime_limit=50
        )
        # T^2 - 3T + 1 splits over F_p iff disc 5 is square (p=5: double root).
        # p=2 is an extra failure (3≡1, no unit solution to the system).
        self.assertEqual(r["asymptotic"]["pattern"], "mixed")
        for p in r["passed_primes"]:
            self.assertTrue(is_quadratic_residue(5, p))
        for p in r["failed_primes"]:
            if p == 2:
                continue
            self.assertFalse(is_quadratic_residue(5, p))

    # --- quantifier alternation ---

    def test_forall_a_exists_sqrt(self):
        r = scan_primes(
            self.adv.predicate_forall_a_exists_sqrt_one_plus_a_t,
            prime_limit=25,
            precision=16,
        )
        self.assertEqual(r["asymptotic"]["pattern"], "eventually_true")
        self.assertEqual(r["failed_primes"], [2])

    def test_exists_nonsquare_sigma2(self):
        r = scan_primes(
            self.adv.predicate_exists_nonsquare_forall_not_square, prime_limit=30
        )
        self.assertEqual(r["asymptotic"]["pattern"], "eventually_true")
        self.assertEqual(r["failed_primes"], [2])

    def test_artin_schreier_not_surjective(self):
        r = scan_primes(
            self.adv.predicate_forall_a_exists_artin_schreier_preimage,
            prime_limit=25,
        )
        self.assertEqual(r["asymptotic"]["pattern"], "always_false")

    def test_quadratic_forall_eventually_false(self):
        r = scan_primes(
            self.adv.predicate_forall_a_quadratic_T2_aT_1_splits, prime_limit=30
        )
        self.assertIn(r["asymptotic"]["pattern"], ("eventually_false", "always_false"))
        self.assertNotIn(5, r["passed_primes"])

    def test_forall_odd_val_not_square(self):
        r = scan_primes(
            self.adv.predicate_forall_val_in_window_even_of_squares,
            prime_limit=20,
            precision=15,
        )
        self.assertEqual(r["asymptotic"]["pattern"], "always_true")

    def test_exists_uniform_base(self):
        r = scan_primes(
            self.adv.predicate_exists_uniform_square_root_base,
            prime_limit=20,
            precision=15,
        )
        self.assertEqual(r["asymptotic"]["pattern"], "eventually_true")

    # --- value group / angular component ---

    def test_uniformizer_ac_one(self):
        r = scan_primes(self.adv.predicate_exists_uniformizer_ac_one, prime_limit=20)
        self.assertEqual(r["asymptotic"]["pattern"], "always_true")

    def test_val_one_nonsquare_ac(self):
        r = scan_primes(
            self.adv.predicate_exists_val_one_with_nonsquare_ac, prime_limit=30
        )
        self.assertEqual(r["asymptotic"]["pattern"], "eventually_true")
        self.assertEqual(r["failed_primes"], [2])

    def test_even_val_nonsquare_ac(self):
        r = scan_primes(
            self.adv.predicate_exists_even_valuation_nonsquare_ac,
            prime_limit=30,
            precision=15,
        )
        self.assertEqual(r["asymptotic"]["pattern"], "eventually_true")
        self.assertEqual(r["failed_primes"], [2])

    def test_value_group_not_2_divisible(self):
        r = scan_primes(
            self.adv.predicate_value_group_is_2_divisible, prime_limit=20
        )
        self.assertEqual(r["asymptotic"]["pattern"], "always_false")

    def test_ultrametric_cancellation(self):
        r = scan_primes(
            self.adv.predicate_ultrametric_cancellation, prime_limit=20
        )
        self.assertEqual(r["asymptotic"]["pattern"], "always_true")

    def test_ac_multiplicative(self):
        r = scan_primes(
            self.adv.predicate_ac_multiplicative_on_samples, prime_limit=20, precision=15
        )
        self.assertEqual(r["asymptotic"]["pattern"], "always_true")
        self.assertEqual(r["error_primes"], [])

    def test_frobenius_gap_valuation(self):
        r = scan_primes(
            self.adv.predicate_valuation_of_frobenius_gap, prime_limit=20, precision=20
        )
        self.assertEqual(r["asymptotic"]["pattern"], "always_true")
        self.assertEqual(r["error_primes"], [])

    def test_compatible_square_criterion(self):
        r = scan_primes(
            self.adv.predicate_compatible_v_ac_square_criterion_on_units,
            prime_limit=30,
            precision=12,
        )
        self.assertEqual(r["asymptotic"]["pattern"], "always_true")

    def test_cli_lists_advanced_predicates(self):
        import io
        from contextlib import redirect_stderr
        from ake_scanner.cli import main

        err = io.StringIO()
        with redirect_stderr(err):
            code = main(["examples/advanced_sentences.py", "-l", "3"])
        self.assertEqual(code, 1)
        msg = err.getvalue()
        self.assertIn("predicate_sum_of_two_squares_equals_t", msg)
        self.assertIn("predicate_forall_a_exists_sqrt_one_plus_a_t", msg)
        self.assertIn("predicate_exists_even_valuation_nonsquare_ac", msg)


if __name__ == "__main__":
    unittest.main()
