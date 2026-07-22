import unittest
import json
import io
from contextlib import redirect_stdout, redirect_stderr

import _pathsetup  # noqa: F401
from ake_scanner.logic.scanner import (
    is_prime,
    generate_primes,
    sieve_primes,
    scan_primes,
    FieldFactory,
    results_to_jsonable,
    classify_asymptotic,
)
from ake_scanner.cli import format_text_report, format_csv_report, main


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

    def test_generate_primes_start(self):
        primes = list(generate_primes(20, start=10))
        self.assertEqual(primes, [11, 13, 17, 19])

    def test_sieve_primes(self):
        self.assertEqual(sieve_primes(10), [2, 3, 5, 7])
        self.assertEqual(sieve_primes(20, start=10), [11, 13, 17, 19])

    def test_field_factory(self):
        ff = FieldFactory(prime=7, precision=10)
        t = ff.t
        self.assertEqual(t.prime, 7)
        self.assertEqual(t.valuation, 1)
        self.assertTrue(ff.one().coeffs.get(0) == 1)
        self.assertTrue(ff.zero().is_zero())

    def test_scan_primes_trivial(self):
        def always_true(F):
            return True

        results = scan_primes(always_true, prime_limit=5)
        self.assertEqual(results["verified_count"], 3)
        self.assertEqual(results["passed_primes"], [2, 3, 5])
        self.assertEqual(results["failed_primes"], [])
        self.assertEqual(results["error_primes"], [])
        self.assertEqual(results["holds_for_p_greater_than"], 0)
        self.assertEqual(results["asymptotic"]["pattern"], "always_true")

    def test_scan_primes_conditional(self):
        def only_two(F):
            return F.prime == 2

        results = scan_primes(only_two, prime_limit=5)
        self.assertEqual(results["verified_count"], 1)
        self.assertEqual(results["passed_primes"], [2])
        self.assertEqual(results["failed_primes"], [3, 5])
        self.assertEqual(results["first_failure"], 3)
        self.assertIsNone(results["holds_for_p_greater_than"])
        self.assertEqual(results["asymptotic"]["pattern"], "eventually_false")
        self.assertEqual(results["asymptotic"]["threshold"], 2)

    def test_scan_errors_separate_from_failures(self):
        def boom(F):
            if F.prime == 3:
                raise RuntimeError("boom")
            return True

        results = scan_primes(boom, prime_limit=7)
        self.assertEqual(results["passed_primes"], [2, 5, 7])
        self.assertEqual(results["failed_primes"], [])
        self.assertEqual(results["error_primes"], [3])
        self.assertEqual(results["error_count"], 1)
        self.assertIn(3, results["details"])
        self.assertEqual(results["first_error"], 3)
        self.assertEqual(results["holds_for_p_greater_than"], 3)
        self.assertEqual(results["asymptotic"]["pattern"], "eventually_true")
        self.assertEqual(results["asymptotic"]["exceptional_primes"], [3])

    def test_scan_explicit_primes(self):
        def always_true(F):
            return True

        results = scan_primes(always_true, primes=[5, 11, 3])
        self.assertEqual(results["passed_primes"], [3, 5, 11])

    def test_asymptotic_threshold_hensel_style(self):
        def one_plus_t_square_style(F):
            return F.prime != 2

        results = scan_primes(one_plus_t_square_style, prime_limit=20)
        self.assertEqual(results["failed_primes"], [2])
        self.assertEqual(results["holds_for_p_greater_than"], 2)
        a = results["asymptotic"]
        self.assertEqual(a["pattern"], "eventually_true")
        self.assertEqual(a["threshold"], 2)
        self.assertEqual(a["exceptional_primes"], [2])
        self.assertGreater(a["tail_count"], 0)
        self.assertEqual(a["tail_passed"], a["tail_count"])

    def test_mixed_pattern_mod4(self):
        """-1 square style: true for p=2 and p≡1 mod 4 — never settles."""

        def minus_one_square(F):
            p = F.prime
            if p == 2:
                return True
            return p % 4 == 1

        results = scan_primes(minus_one_square, prime_limit=30)
        self.assertEqual(results["asymptotic"]["pattern"], "mixed")
        self.assertIsNone(results["asymptotic"]["threshold"])

    def test_classify_always_false(self):
        a = classify_asymptotic(
            passed=[],
            failed=[2, 3, 5],
            errors=[],
            primes_scanned=[2, 3, 5],
        )
        self.assertEqual(a["pattern"], "always_false")

    def test_jsonable(self):
        results = scan_primes(lambda F: True, prime_limit=5)
        data = results_to_jsonable(results)
        json.dumps(data)  # must not raise
        self.assertIn("asymptotic", data)

    def test_format_text_asymptotic_first(self):
        results = scan_primes(lambda F: F.prime > 3, prime_limit=7)
        text = format_text_report(results)
        self.assertIn("AKE asymptotic summary", text)
        self.assertIn("eventually_true", text)
        self.assertIn("Threshold N:", text)
        self.assertIn("Exceptional:", text)
        # Default: no full passed list
        self.assertNotIn("Passed primes:", text)

        verbose = format_text_report(results, verbose=True)
        self.assertIn("Failed primes:", verbose)

        csv_out = format_csv_report(results)
        self.assertIn("prime,status,detail", csv_out)
        self.assertIn("2,failed", csv_out)
        self.assertIn("5,passed", csv_out)


class TestCLI(unittest.TestCase):
    def test_cli_json(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(
                [
                    "examples/demo_hensel.py",
                    "predicate_one_plus_t_is_square",
                    "--limit",
                    "15",
                    "--precision",
                    "15",
                    "--json",
                ]
            )
        self.assertEqual(code, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["failed_primes"], [2])
        self.assertEqual(data["holds_for_p_greater_than"], 2)
        self.assertEqual(data["asymptotic"]["pattern"], "eventually_true")

    def test_cli_lists_predicates_when_name_omitted(self):
        err = io.StringIO()
        with redirect_stderr(err):
            code = main(["examples/demo_hensel.py", "-l", "5"])
        self.assertEqual(code, 1)
        msg = err.getvalue()
        self.assertIn("Multiple predicates", msg)
        self.assertIn("predicate_one_plus_t_is_square", msg)
        self.assertIn("predicate_t_is_square", msg)
        self.assertIn("predicate_one_plus_t_is_cube", msg)
        self.assertIn("predicate_minus_one_is_square", msg)
        self.assertIn("predicate_x_cubed_minus_x_equals_t", msg)
        self.assertIn("predicate_artin_schreier_valuation_obstruction", msg)

    def test_cli_asymptotic_text(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(
                [
                    "examples/demo_hensel.py",
                    "predicate_one_plus_t_is_square",
                    "-l",
                    "20",
                    "-q",
                ]
            )
        self.assertEqual(code, 0)
        out = buf.getvalue()
        self.assertIn("eventually_true", out)
        self.assertIn("Exceptional:", out)
        self.assertIn("p > 2", out)


if __name__ == "__main__":
    unittest.main()
