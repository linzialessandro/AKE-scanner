"""Prime-range scanner for predicates over F_p((t))."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Sequence, Union

from ake_scanner.algebra.laurent import LaurentSeries
from ake_scanner.logic.asymptotic import analyze_results, classify_asymptotic
from ake_scanner.logic.primes import (
    generate_primes,
    is_prime,
    normalize_prime_list,
    sieve_primes,
)
from ake_scanner.logic.verdict import (
    CODE_RUNTIME,
    Verdict,
    coerce_verdict,
    fail,
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
    "Verdict",
]


# Predicate may return bool (legacy) or Verdict (structured explain).
PredicateResult = Union[bool, Verdict]
Predicate = Callable[["FieldFactory"], PredicateResult]


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
    predicate: Predicate,
    prime_limit: Optional[int] = None,
    precision: int = 20,
    start: int = 2,
    primes: Optional[Sequence[int]] = None,
    progress: bool = False,
    on_progress: Optional[Callable[[int, int, int, str], None]] = None,
    explain: bool = False,
) -> Dict[str, Any]:
    """
    Run the predicate against F_p((t)) for a range of primes.

    Distinguishes mathematical failure (predicate returned False / failing
    Verdict) from runtime errors (exceptions). The report emphasizes AKE-style
    asymptotics under the ``asymptotic`` key.

    The predicate may return ``bool`` or a :class:`Verdict`. With
    ``explain=True`` (or whenever a ``Verdict`` is returned), per-prime
    explanations are stored under ``results["explanations"]`` keyed by prime.

    ``on_progress``, if given, is called after each prime as
    ``on_progress(done, total, prime, status)`` with status in
    ``{"pass", "fail", "error"}``.
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
        "explanations": {},
        "first_failure": None,
        "first_error": None,
        "holds_for_p_greater_than": None,
        "asymptotic": {},
        "precision": precision,
        "primes_scanned": [],
        "start": start,
        "prime_limit": prime_limit,
        "explain": explain,
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
            raw = predicate(factory)
            # Structured Verdict always recorded; bare bool only if explain=True
            if isinstance(raw, Verdict):
                verdict = raw
                store_explain = True
            else:
                verdict = coerce_verdict(raw)
                store_explain = explain

            if verdict.holds:
                results["verified_count"] += 1
                results["passed_primes"].append(p)
                status = "pass"
            else:
                results["failed_count"] += 1
                results["failed_primes"].append(p)
                status = "fail"
                if results["first_failure"] is None:
                    results["first_failure"] = p

            if store_explain:
                results["explanations"][p] = verdict.to_dict()
        except Exception as e:
            results["error_count"] += 1
            results["error_primes"].append(p)
            msg = f"{type(e).__name__}: {e}"
            results["details"][p] = msg
            results["explanations"][p] = fail(CODE_RUNTIME, msg, prime=p).to_dict()
            status = "error"
            if results["first_error"] is None:
                results["first_error"] = p

        if on_progress is not None:
            try:
                on_progress(idx + 1, total, p, status)
            except Exception:
                pass

    return analyze_results(results)


def results_to_jsonable(results: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure report is JSON-serializable (keys of details/explanations as strings)."""
    out = dict(results)
    out["details"] = {str(k): v for k, v in results.get("details", {}).items()}
    expl = results.get("explanations") or {}
    out["explanations"] = {str(k): v for k, v in expl.items()}
    return out
