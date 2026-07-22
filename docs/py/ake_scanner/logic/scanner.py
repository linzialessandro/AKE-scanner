"""Prime-range scanner for predicates over F_p((t))."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence

from ake_scanner.algebra.laurent import LaurentSeries


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


def is_prime(n: int) -> bool:
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True


def generate_primes(limit: int, start: int = 2):
    """Yield primes in [start, limit]."""
    if limit < 2 or start > limit:
        return
    begin = max(2, start)
    if begin <= 2 <= limit:
        yield 2
        begin = 3
    if begin % 2 == 0:
        begin += 1
    for n in range(begin, limit + 1, 2):
        if is_prime(n):
            yield n


def sieve_primes(limit: int, start: int = 2) -> List[int]:
    """Return all primes in [start, limit] via the sieve of Eratosthenes."""
    if limit < 2:
        return []
    sieve = bytearray(b"\x01") * (limit + 1)
    sieve[0:2] = b"\x00\x00"
    for i in range(2, int(limit**0.5) + 1):
        if sieve[i]:
            step = i
            start_mul = i * i
            sieve[start_mul : limit + 1 : step] = b"\x00" * (
                ((limit - start_mul) // step) + 1
            )
    begin = max(2, start)
    return [i for i in range(begin, limit + 1) if sieve[i]]


def _normalize_prime_list(
    prime_limit: Optional[int],
    start: int,
    primes: Optional[Sequence[int]],
) -> List[int]:
    if primes is not None:
        return sorted({p for p in primes if is_prime(p) and p >= start})
    if prime_limit is None:
        raise ValueError("Either prime_limit or primes must be provided")
    if prime_limit <= 10_000:
        return list(generate_primes(prime_limit, start=start))
    return sieve_primes(prime_limit, start=start)


def _threshold_all_pass_after(
    passed: List[int], blockers: List[int]
) -> Optional[int]:
    """
    Smallest N among candidates such that every scanned prime p > N passed.

    Returns 0 if there are passes and no blockers; None if no such N exists.
    """
    if not passed:
        return None
    if not blockers:
        return 0
    N = max(blockers)
    if any(p > N for p in passed) and not any(b > N for b in blockers):
        return N
    return None


def _threshold_all_fail_after(
    failed: List[int], non_failures: List[int]
) -> Optional[int]:
    """
    N such that every scanned prime p > N failed (returned False).

    non_failures = passed ∪ errors (anything that was not a clean False).
    """
    if not failed:
        return None
    if not non_failures:
        return 0  # all scanned primes failed
    N = max(non_failures)
    if any(p > N for p in failed) and not any(q > N for q in non_failures):
        return N
    return None


def _min_tail_size(n_scanned: int) -> int:
    """
    Require a substantial clean tail before claiming eventually_true/false.

    A single lucky pass at the top of the range must not look like AKE
    stabilization (e.g. p ≡ 1 mod 4 ending on one residue-1 prime).
    Demand at least 2 primes and about 25% of the sample in the tail.
    """
    if n_scanned <= 0:
        return 1
    return max(2, (n_scanned + 3) // 4)


def classify_asymptotic(
    passed: List[int],
    failed: List[int],
    errors: List[int],
    primes_scanned: List[int],
) -> Dict[str, Any]:
    """
    Classify the scan into an AKE-style asymptotic pattern.

    Patterns
    --------
    - ``always_true``: every scanned prime passed
    - ``always_false``: every scanned prime failed (no passes, no errors)
    - ``eventually_true``: exists N with all scanned p > N passed, and the
      clean tail is large enough to be meaningful
    - ``eventually_false``: exists N with all scanned p > N failed (same tail rule)
    - ``mixed``: no reliable single threshold (oscillation, or tail too short)

    The interesting AKE readout is primarily ``eventually_true`` /
    ``eventually_false`` together with the exceptional (sub-threshold) primes.
    """
    blockers = failed + errors
    thr_true = _threshold_all_pass_after(passed, blockers)
    thr_false = _threshold_all_fail_after(failed, passed + errors)

    largest = max(primes_scanned) if primes_scanned else None
    n_scanned = len(primes_scanned)
    min_tail = _min_tail_size(n_scanned)

    pattern = "mixed"
    threshold: Optional[int] = None
    exceptional: List[int] = sorted(set(blockers))
    tail: List[int] = []
    summary = "no single threshold in scanned range"
    tail_ok = False

    if thr_true == 0 and not blockers:
        pattern = "always_true"
        threshold = 0
        exceptional = []
        tail = list(primes_scanned)
        summary = "holds for all scanned primes"
        tail_ok = True
    elif thr_false == 0 and not passed and not errors and failed:
        pattern = "always_false"
        threshold = 0
        exceptional = []
        tail = list(primes_scanned)
        summary = "fails for all scanned primes"
        tail_ok = True
    elif thr_true is not None:
        candidate_tail = [p for p in primes_scanned if p > thr_true]
        if len(candidate_tail) >= min_tail:
            pattern = "eventually_true"
            threshold = thr_true
            exceptional = sorted(p for p in blockers if p <= thr_true)
            tail = candidate_tail
            summary = f"holds for all scanned p > {thr_true}"
            tail_ok = True
        else:
            summary = (
                f"raw threshold p > {thr_true} has only {len(candidate_tail)} "
                f"tail prime(s); need ≥ {min_tail} for a stable claim "
                f"(possible oscillation)"
            )
            exceptional = sorted(set(blockers))
    elif thr_false is not None:
        candidate_tail = [p for p in primes_scanned if p > thr_false]
        if len(candidate_tail) >= min_tail:
            pattern = "eventually_false"
            threshold = thr_false
            exceptional = sorted(p for p in (passed + errors) if p <= thr_false)
            tail = candidate_tail
            summary = f"fails for all scanned p > {thr_false}"
            tail_ok = True
        else:
            summary = (
                f"raw fail-threshold p > {thr_false} has only "
                f"{len(candidate_tail)} tail prime(s); need ≥ {min_tail}"
            )
            exceptional = sorted(set(blockers))

    if pattern == "mixed":
        last_blocker = max(blockers) if blockers else None
        last_pass = max(passed) if passed else None
        if last_blocker is not None and last_pass is not None and "raw" not in summary:
            summary += (
                f" (last pass p={last_pass}, last failure/error p={last_blocker})"
            )

    tail_pass = sum(1 for p in tail if p in set(passed))
    tail_fail = sum(1 for p in tail if p in set(failed))
    tail_err = sum(1 for p in tail if p in set(errors))

    # holds_for_p_greater_than: only when we confidently claim eventually_true
    holds = threshold if pattern == "eventually_true" else (
        0 if pattern == "always_true" else None
    )

    return {
        "pattern": pattern,
        "threshold": threshold,
        "summary": summary,
        "exceptional_primes": exceptional,
        "tail_primes": tail,
        "tail_count": len(tail),
        "tail_passed": tail_pass,
        "tail_failed": tail_fail,
        "tail_errors": tail_err,
        "min_tail_required": min_tail,
        "tail_sufficient": tail_ok if pattern.startswith("eventually") or pattern.startswith("always") else False,
        "largest_prime_scanned": largest,
        "primes_scanned_count": n_scanned,
        "holds_for_p_greater_than": holds,
    }


def analyze_results(results: Dict[str, Any]) -> Dict[str, Any]:
    """Attach / refresh the ``asymptotic`` block on a scan report."""
    asymptotic = classify_asymptotic(
        results.get("passed_primes", []),
        results.get("failed_primes", []),
        results.get("error_primes", []),
        results.get("primes_scanned", []),
    )
    results["asymptotic"] = asymptotic
    results["holds_for_p_greater_than"] = asymptotic["holds_for_p_greater_than"]
    return results


def scan_primes(
    predicate: Callable[[FieldFactory], bool],
    prime_limit: Optional[int] = None,
    precision: int = 20,
    start: int = 2,
    primes: Optional[Sequence[int]] = None,
    progress: bool = False,
) -> Dict[str, Any]:
    """
    Run the predicate against F_p((t)) for a range of primes.

    Distinguishes mathematical failure (predicate returned False) from
    runtime errors (exceptions). The report emphasizes AKE-style asymptotics
    under the ``asymptotic`` key (pattern, threshold, exceptional primes).
    """
    prime_list = _normalize_prime_list(prime_limit, start, primes)

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
        try:
            is_valid = predicate(factory)
            if is_valid:
                results["verified_count"] += 1
                results["passed_primes"].append(p)
            else:
                results["failed_count"] += 1
                results["failed_primes"].append(p)
                if results["first_failure"] is None:
                    results["first_failure"] = p
        except Exception as e:
            results["error_count"] += 1
            results["error_primes"].append(p)
            results["details"][p] = f"{type(e).__name__}: {e}"
            if results["first_error"] is None:
                results["first_error"] = p

    return analyze_results(results)


def results_to_jsonable(results: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure report is JSON-serializable (keys of details as strings)."""
    out = dict(results)
    out["details"] = {str(k): v for k, v in results.get("details", {}).items()}
    return out
