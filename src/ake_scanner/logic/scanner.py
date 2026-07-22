"""Prime-range scanner for predicates over F_p((t))."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Sequence

from ake_scanner.algebra.laurent import LaurentSeries
from ake_scanner.logic.asymptotic import analyze_results, classify_asymptotic
from ake_scanner.logic.primes import (
    generate_primes,
    is_prime,
    normalize_prime_list,
    sieve_primes,
)

# Re-exports for stable import paths (tests / external code).
__all__ = [
    "FieldFactory",
    "scan_primes",
    "results_to_jsonable",
    "is_prime",
    "generate_primes",
    "sieve_primes",
    "normalize_prime_list",
    "classify_asymptotic",
    "analyze_results",
]


class FieldFactory:
    """
    Passed to the user's predicate function.
    Allows creating elements in the field F_p((t)).
    """

    def __init__(self, prime: int, precision: int):
        self.prime = prime
        self.precision = precision

    @property
    def t(self) -> LaurentSeries:
        return LaurentSeries.t(self.prime, self.precision)

    def constant(self, n: int) -> LaurentSeries:
        return LaurentSeries.constant(n, self.prime, self.precision)

    def element(self, coeffs: Dict[int, int]) -> LaurentSeries:
        return LaurentSeries(coeffs, self.prime, self.precision)

    def zero(self) -> LaurentSeries:
        return LaurentSeries.zero(self.prime, self.precision)

    def one(self) -> LaurentSeries:
        return LaurentSeries.one(self.prime, self.precision)


def scan_primes(
    predicate: Callable[[FieldFactory], bool],
    prime_limit: Optional[int] = None,
    precision: int = 20,
    start: int = 2,
    primes: Optional[Sequence[int]] = None,
    progress: bool = False,
    on_progress: Optional[Callable[[int, int, int, str], None]] = None,
) -> Dict[str, Any]:
    """
    Run the predicate against F_p((t)) for a range of primes.

    Distinguishes mathematical failure (predicate returned False) from
    runtime errors (exceptions). The report emphasizes AKE-style asymptotics
    under the ``asymptotic`` key (pattern, threshold, exceptional primes).

    ``on_progress``, if given, is called after each prime as
    ``on_progress(done, total, prime, status)`` with status in
    ``{"pass", "fail", "error"}``. Useful for UIs / workers.
    """
    prime_list = normalize_prime_list(prime_limit, start, primes)

    results: Dict[str, Any] = {
        "verified_count": 0,
        "failed_count": 0,
        "error_count": 0,
        "passed_primes": [],
        "failed_primes": [],
        "error_primes": [],
        "details": {},
        "first_failure": None,
        "first_error": None,
        "holds_for_p_greater_than": None,
        "asymptotic": {},
        "precision": precision,
        "primes_scanned": [],
        "start": start,
        "prime_limit": prime_limit,
    }

    total = len(prime_list)
    for idx, p in enumerate(prime_list):
        results["primes_scanned"].append(p)
        if progress and total:
            if idx == 0 or idx + 1 == total or (idx + 1) % max(1, total // 20) == 0:
                print(f"  … {idx + 1}/{total} primes (p={p})", flush=True)

        factory = FieldFactory(p, precision)
        status = "error"
        try:
            is_valid = predicate(factory)
            if is_valid:
                results["verified_count"] += 1
                results["passed_primes"].append(p)
                status = "pass"
            else:
                results["failed_count"] += 1
                results["failed_primes"].append(p)
                status = "fail"
                if results["first_failure"] is None:
                    results["first_failure"] = p
        except Exception as e:
            results["error_count"] += 1
            results["error_primes"].append(p)
            results["details"][p] = f"{type(e).__name__}: {e}"
            status = "error"
            if results["first_error"] is None:
                results["first_error"] = p

        if on_progress is not None:
            try:
                on_progress(idx + 1, total, p, status)
            except Exception:
                # Never let a UI callback abort the scan.
                pass

    return analyze_results(results)


def results_to_jsonable(results: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure report is JSON-serializable (keys of details as strings)."""
    out = dict(results)
    out["details"] = {str(k): v for k, v in results.get("details", {}).items()}
    return out
