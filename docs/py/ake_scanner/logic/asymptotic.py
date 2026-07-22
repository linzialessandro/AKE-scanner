"""AKE-style asymptotic classification of scan results."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def threshold_all_pass_after(
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


def threshold_all_fail_after(
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


def min_tail_size(n_scanned: int) -> int:
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
    - ``empty``: no primes were scanned (vacuous sample)
    - ``always_true``: every scanned prime passed
    - ``always_false``: every scanned prime failed (no passes, no errors)
    - ``eventually_true``: exists N with all scanned p > N passed, and the
      clean tail is large enough to be meaningful
    - ``eventually_false``: exists N with all scanned p > N failed (same tail rule)
    - ``mixed``: no reliable single threshold (oscillation, or tail too short)

    The interesting AKE readout is primarily ``eventually_true`` /
    ``eventually_false`` together with the exceptional (sub-threshold) primes.
    """
    n_scanned = len(primes_scanned)
    if n_scanned == 0:
        return {
            "pattern": "empty",
            "threshold": None,
            "summary": "no primes scanned (empty range)",
            "exceptional_primes": [],
            "tail_primes": [],
            "tail_count": 0,
            "tail_passed": 0,
            "tail_failed": 0,
            "tail_errors": 0,
            "min_tail_required": min_tail_size(0),
            "tail_sufficient": False,
            "largest_prime_scanned": None,
            "primes_scanned_count": 0,
            "holds_for_p_greater_than": None,
        }

    blockers = failed + errors
    thr_true = threshold_all_pass_after(passed, blockers)
    thr_false = threshold_all_fail_after(failed, passed + errors)

    largest = max(primes_scanned)
    min_tail = min_tail_size(n_scanned)

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
