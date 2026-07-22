"""Text / CSV report formatting for scan results."""

from __future__ import annotations

import csv
import io


def format_text_report(
    results: dict,
    verbose: bool = False,
    full: bool = False,
) -> str:
    """
    Default report is AKE-asymptotic-first: pattern, threshold N, exceptional
    primes, and the clean tail. Use verbose/full for per-prime inventories.
    """
    a = results.get("asymptotic") or {}
    pattern = a.get("pattern", "unknown")
    threshold = a.get("threshold")
    summary = a.get("summary", "")
    exceptional = a.get("exceptional_primes", [])
    tail_count = a.get("tail_count", 0)
    largest = a.get("largest_prime_scanned")
    n_scanned = a.get("primes_scanned_count", len(results.get("primes_scanned", [])))

    lines = [
        "--- AKE asymptotic summary ---",
        f"Pattern:       {pattern}",
        f"Claim:         {summary}",
    ]

    if threshold is not None:
        lines.append(f"Threshold N:   {threshold}")
    else:
        lines.append("Threshold N:   (none in scanned range)")

    if pattern == "eventually_true":
        lines.append(
            f"Exceptional:   {exceptional if exceptional else '(none)'}"
        )
    elif pattern == "eventually_false":
        lines.append(
            f"Early non-fail: {exceptional if exceptional else '(none)'}"
        )
    elif pattern == "mixed" and exceptional:
        lines.append(f"Non-passes:    {exceptional}")
    elif pattern in ("always_true", "always_false"):
        lines.append("Exceptional:   (none)")

    if pattern in ("eventually_true", "always_true"):
        if tail_count:
            span = f" (up to p={largest})" if largest is not None else ""
            lines.append(f"Clean tail:    {tail_count} primes{span}, all passed")
        else:
            lines.append("Clean tail:    (empty)")
    elif pattern in ("eventually_false", "always_false"):
        if tail_count:
            span = f" (up to p={largest})" if largest is not None else ""
            lines.append(f"Failing tail:  {tail_count} primes{span}, all failed")
        else:
            lines.append("Failing tail:  (empty)")
    else:
        span = f" up to p={largest}" if largest is not None else ""
        lines.append(f"Scanned span:  {n_scanned} primes{span}")

    lines.extend(
        [
            f"Counts:        pass={results['verified_count']}  "
            f"fail={results['failed_count']}  err={results['error_count']}  "
            f"total={n_scanned}",
            f"Precision:     {results['precision']}",
        ]
    )

    if results.get("error_primes"):
        lines.append(f"Error primes:  {results['error_primes']}")
        if results.get("details"):
            for p, error in results["details"].items():
                lines.append(f"  p={p}: {error}")

    # Guidance line
    if pattern == "eventually_true":
        lines.append(
            "Readout:       AKE-style evidence that φ holds for large p "
            f"(check larger --limit to stress-test N={threshold})."
        )
    elif pattern == "eventually_false":
        lines.append(
            "Readout:       AKE-style evidence that φ fails for large p."
        )
    elif pattern == "mixed":
        lines.append(
            "Readout:       No eventual constant truth value in range — "
            "look for a congruence condition (e.g. p mod m), not a single N."
        )
    elif pattern == "always_true":
        lines.append(
            "Readout:       Holds on entire scanned range (including small p)."
        )
    elif pattern == "always_false":
        lines.append(
            "Readout:       Fails on entire scanned range."
        )

    if full or verbose:
        lines.append("")
        lines.append("--- Detail ---")
        if results.get("failed_primes"):
            lines.append(f"Failed primes: {results['failed_primes']}")
        if results.get("passed_primes") and (full or verbose):
            lines.append(f"Passed primes: {results['passed_primes']}")
        if full and a.get("tail_primes") is not None:
            lines.append(f"Tail primes:   {a.get('tail_primes')}")

    expl = results.get("explanations") or {}
    if expl and (verbose or full or results.get("explain")):
        lines.append("")
        lines.append("--- Explanations (per prime) ---")
        for p in results.get("primes_scanned") or sorted(expl.keys(), key=lambda x: int(x)):
            key = p if p in expl else str(p)
            # keys may be int or already str depending on path
            entry = expl.get(p, expl.get(str(p)))
            if not entry:
                continue
            holds = entry.get("holds")
            code = entry.get("code", "?")
            msg = entry.get("message", "")
            mark = "pass" if holds else "fail"
            if code == "runtime_error":
                mark = "err"
            line = f"  p={p}: [{mark}] {code}"
            if msg:
                line += f" — {msg}"
            lines.append(line)
            wit = entry.get("witness")
            if wit and (full or verbose):
                if wit.get("kind") == "laurent" and wit.get("coeffs") is not None:
                    coeffs = wit["coeffs"]
                    # compact: show a few terms
                    terms = []
                    for d, c in list(coeffs.items())[:6]:
                        terms.append(f"{c}*t^{d}")
                    more = "…" if wit.get("truncated") or len(coeffs) > 6 else ""
                    lines.append(f"         witness: {', '.join(terms)}{more}")
                elif wit.get("kind") == "residue":
                    lines.append(
                        f"         witness residue root: {wit.get('root')} "
                        f"(value {wit.get('value')} mod {wit.get('prime')})"
                    )

    return "\n".join(lines)


def format_csv_report(results: dict) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["prime", "status", "detail"])
    status_map = {}
    for p in results["passed_primes"]:
        status_map[p] = ("passed", "")
    for p in results["failed_primes"]:
        status_map[p] = ("failed", "")
    for p in results["error_primes"]:
        status_map[p] = ("error", results["details"].get(p, ""))
    for p in results["primes_scanned"]:
        st, detail = status_map.get(p, ("unknown", ""))
        writer.writerow([p, st, detail])
    return buf.getvalue()
