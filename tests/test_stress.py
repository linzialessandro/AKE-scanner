"""Regression stress suite (subset of the interactive stress harness).

Keeps CI sensitive to algebra, diagnose/scan consistency, catalog stability,
and asymptotic edge cases without multi-minute runtimes.
"""

from __future__ import annotations

import json
import random
import unittest

import _pathsetup  # noqa: F401
from ake_scanner.algebra.laurent import LaurentSeries
from ake_scanner.algebra.hensel import (
    is_quadratic_residue,
    solve_x_n_equals,
    sqrt_mod_p,
    sqrt_series,
)
from ake_scanner.logic.asymptotic import classify_asymptotic
from ake_scanner.logic.diagnose import diagnose_x_n_equals
from ake_scanner.logic.primes import generate_primes, is_prime, sieve_primes
from ake_scanner.logic.scanner import FieldFactory, results_to_jsonable, scan_primes
from ake_scanner.reporting import format_csv_report, format_text_report

import importlib
import sys

sys.path.insert(0, "examples")
demo = importlib.import_module("demo_hensel")
adv = importlib.import_module("advanced_sentences")


class TestEmptyAsymptotic(unittest.TestCase):
    def test_empty_scan_pattern(self):
        r = scan_primes(lambda F: True, prime_limit=1)
        self.assertEqual(r["primes_scanned"], [])
        self.assertEqual(r["asymptotic"]["pattern"], "empty")
        self.assertIn("no primes", r["asymptotic"]["summary"])

    def test_empty_classify_direct(self):
        a = classify_asymptotic([], [], [], [])
        self.assertEqual(a["pattern"], "empty")
        self.assertIsNone(a["holds_for_p_greater_than"])

    def test_empty_text_report(self):
        r = scan_primes(lambda F: True, primes=[], prime_limit=None)
        # primes=[] via normalize may need prime_limit — use start>limit
        r = scan_primes(lambda F: True, prime_limit=10, start=100)
        text = format_text_report(r)
        self.assertIn("empty", text.lower())
        self.assertIn("Pattern:       empty", text)


class TestRingFuzz(unittest.TestCase):
    def test_random_commutativity_distributivity(self):
        rng = random.Random(0)
        for _ in range(80):
            p = rng.choice([2, 3, 5, 7, 11, 13, 17])
            prec = rng.randint(6, 25)

            def rs():
                coeffs = {}
                for _ in range(rng.randint(0, 6)):
                    coeffs[rng.randint(-3, prec)] = rng.randint(0, p - 1)
                return LaurentSeries(coeffs, p, prec)

            a, b, c = rs(), rs(), rs()
            self.assertEqual(a + b, b + a)
            self.assertEqual(a * b, b * a)
            self.assertEqual(a * (b + c), a * b + a * c)


class TestSqrtRoundTrip(unittest.TestCase):
    def test_unit_square_residues(self):
        rng = random.Random(1)
        for p in [5, 7, 11, 13, 17]:
            for _ in range(20):
                lead = rng.randint(1, p - 1)
                if not is_quadratic_residue(lead, p):
                    lead = (lead * lead) % p
                coeffs = {0: lead}
                for d in range(1, 4):
                    if rng.random() < 0.4:
                        coeffs[d] = rng.randint(0, p - 1)
                target = LaurentSeries(coeffs, p, 18)
                root = sqrt_series(target, 18)
                self.assertIsNotNone(root)
                sq = root * root
                for d in range(0, 16):
                    self.assertEqual(
                        sq.coeffs.get(d, 0),
                        target.coeffs.get(d, 0),
                        msg=f"p={p} d={d}",
                    )


class TestDiagnoseConsistency(unittest.TestCase):
    def test_diagnose_matches_solve(self):
        for p in generate_primes(40):
            F = FieldFactory(p, 16)
            for n, target in [
                (2, F.constant(1) + F.t),
                (2, F.t),
                (3, F.constant(1) + F.t),
            ]:
                v = diagnose_x_n_equals(target, n, 16)
                sol = solve_x_n_equals(target, n, 16)
                self.assertEqual(v.holds, sol is not None, msg=f"p={p} n={n}")
                if v.holds and sol is not None:
                    diff = sol ** n - target
                    if not diff.is_zero():
                        self.assertGreater(int(diff.valuation), 12)


class TestCatalogScans(unittest.TestCase):
    def test_all_demo_predicates_limit_60(self):
        names = [n for n in dir(demo) if n.startswith("predicate_")]
        self.assertGreaterEqual(len(names), 10)
        for name in names:
            fn = getattr(demo, name)
            r = scan_primes(fn, prime_limit=60, precision=14)
            tot = len(r["primes_scanned"])
            self.assertEqual(
                r["verified_count"] + r["failed_count"] + r["error_count"],
                tot,
                msg=name,
            )
            self.assertIn("pattern", r["asymptotic"])
            self.assertEqual(r["error_count"], 0, msg=f"{name}: {r['details']}")
            results_to_jsonable(r)
            format_text_report(r)
            format_csv_report(r)

    def test_sample_advanced_predicates(self):
        sample = [
            "predicate_sum_of_two_squares_equals_t",
            "predicate_independent_simultaneous_squares",
            "predicate_forall_a_exists_sqrt_one_plus_a_t",
            "predicate_exists_nonsquare_forall_not_square",
            "predicate_value_group_is_2_divisible",
            "predicate_exists_even_valuation_nonsquare_ac",
            "predicate_compatible_v_ac_square_criterion_on_units",
        ]
        for name in sample:
            fn = getattr(adv, name)
            lim = 25 if "forall" in name else 40
            r = scan_primes(fn, prime_limit=lim, precision=12)
            self.assertEqual(r["error_count"], 0, msg=f"{name}: {r['details']}")
            # Advanced preds return Verdict → explanations populated
            self.assertTrue(r["explanations"], msg=name)
            # JSON-safe
            json.dumps(results_to_jsonable(r))


class TestScanEdges(unittest.TestCase):
    def test_exception_is_error_not_fail(self):
        def boom(F):
            if F.prime == 5:
                raise RuntimeError("x")
            return True

        r = scan_primes(boom, prime_limit=12)
        self.assertIn(5, r["error_primes"])
        self.assertNotIn(5, r["failed_primes"])
        self.assertEqual(r["explanations"][5]["code"], "runtime_error")

    def test_explicit_primes_filter(self):
        r = scan_primes(lambda F: True, primes=[4, 5, 6, 7, 9, 11])
        self.assertEqual(r["primes_scanned"], [5, 7, 11])

    def test_minus_one_mod4_consistency(self):
        r = scan_primes(demo.predicate_minus_one_is_square, prime_limit=80, precision=12)
        self.assertEqual(r["asymptotic"]["pattern"], "mixed")
        for p in r["passed_primes"]:
            if p > 2:
                self.assertEqual(p % 4, 1)
        for p in r["failed_primes"]:
            if p > 2:
                self.assertEqual(p % 4, 3)

    def test_determinism(self):
        r1 = scan_primes(demo.predicate_one_plus_t_is_cube, prime_limit=50, precision=14)
        r2 = scan_primes(demo.predicate_one_plus_t_is_cube, prime_limit=50, precision=14)
        self.assertEqual(r1["passed_primes"], r2["passed_primes"])
        self.assertEqual(r1["asymptotic"], r2["asymptotic"])

    def test_sieve_matches_generate(self):
        self.assertEqual(sieve_primes(500), list(generate_primes(500)))
        self.assertTrue(all(is_prime(p) for p in sieve_primes(200)))


class TestTonelliInStress(unittest.TestCase):
    def test_large_p_sqrt_quick(self):
        p = 10007
        a = (4242 * 4242) % p
        r = sqrt_mod_p(a, p)
        self.assertIsNotNone(r)
        self.assertEqual((r * r) % p, a)


if __name__ == "__main__":
    unittest.main()
