"""Command-line interface for AKE Scanner."""

from __future__ import annotations

import argparse
import csv
import inspect
import io
import json
import os
import sys
import importlib.util
from types import ModuleType
from typing import Callable, List, Optional, Sequence, Tuple

from ake_scanner.logic.scanner import (
    FieldFactory,
    scan_primes,
    results_to_jsonable,
    is_prime,
)


def _load_module(file_path: str) -> ModuleType:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    module_name = os.path.splitext(os.path.basename(file_path))[0]
    # Unique name so reloads from different paths do not clash
    unique_name = f"ake_user_predicate_{module_name}_{abs(hash(os.path.abspath(file_path)))}"
    spec = importlib.util.spec_from_file_location(unique_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {file_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        raise ImportError(f"Error executing module {file_path}: {e}") from e
    return module


def _looks_like_predicate(name: str, func: Callable) -> bool:
    """
    Heuristic for scan predicates: public callable with one required
    positional parameter that is a field factory (name F / factory / …),
    or a function whose name starts with ``predicate_``.
    """
    try:
        sig = inspect.signature(func)
    except (TypeError, ValueError):
        return False
    required = [
        p
        for p in sig.parameters.values()
        if p.default is inspect.Parameter.empty
        and p.kind
        in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        )
    ]
    if len(required) != 1:
        return False
    if name.startswith("predicate_"):
        return True
    first = required[0].name.lower()
    return first in ("f", "factory", "field", "field_factory", "ff")


def list_predicates(module: ModuleType) -> List[Tuple[str, Callable]]:
    """
    Public callables defined in the module that look like predicates
    (one required argument, e.g. FieldFactory -> bool).
    """
    found: List[Tuple[str, Callable]] = []
    for name, obj in sorted(vars(module).items()):
        if name.startswith("_"):
            continue
        if not callable(obj):
            continue
        # Prefer functions defined in this module (skip re-exports of helpers)
        if inspect.isfunction(obj) and getattr(obj, "__module__", None) != module.__name__:
            continue
        if not _looks_like_predicate(name, obj):
            continue
        found.append((name, obj))
    return found


def load_predicate_from_file(
    file_path: str, function_name: str
) -> Callable[[FieldFactory], bool]:
    """Dynamically load a predicate function from a Python file."""
    module = _load_module(file_path)
    if not hasattr(module, function_name):
        available = [n for n, _ in list_predicates(module)]
        hint = f" Available predicates: {', '.join(available)}" if available else ""
        raise AttributeError(
            f"Function '{function_name}' not found in {file_path}.{hint}"
        )

    func = getattr(module, function_name)
    if not callable(func):
        raise TypeError(f"'{function_name}' is not callable")

    return func


def resolve_predicate(
    file_path: str, function_name: Optional[str]
) -> Tuple[str, Callable[[FieldFactory], bool]]:
    """
    Resolve which predicate to run.

    - If ``function_name`` is given, load it.
    - If omitted and exactly one predicate is found, use it.
    - If omitted and several are found, raise with a list to choose from.
    """
    if function_name:
        return function_name, load_predicate_from_file(file_path, function_name)

    module = _load_module(file_path)
    preds = list_predicates(module)
    if not preds:
        raise AttributeError(
            f"No predicate functions found in {file_path}. "
            "Define a function that takes one argument (FieldFactory) and returns bool."
        )
    if len(preds) == 1:
        name, func = preds[0]
        return name, func

    names = ", ".join(n for n, _ in preds)
    raise SystemExit(
        f"Multiple predicates in {file_path}. Specify one:\n"
        + "\n".join(f"  ake-scan {file_path} {n}" for n, _ in preds)
        + f"\n\nAvailable: {names}"
    )


def _parse_primes(s: str) -> List[int]:
    parts = [p.strip() for p in s.split(",") if p.strip()]
    primes = []
    for part in parts:
        n = int(part)
        if not is_prime(n):
            raise argparse.ArgumentTypeError(f"{n} is not prime")
        primes.append(n)
    return primes


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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ake-scan",
        description=(
            "AKE-scanner: empirically check sentences in F_p((t)), with "
            "reports focused on the asymptotic pattern (threshold N, "
            "exceptional primes, clean tail). "
            "If function_name is omitted, lists predicates (or runs the only one)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  ake-scan examples/demo_hensel.py predicate_one_plus_t_is_square -l 100\n"
            "  ake-scan examples/demo_hensel.py predicate_minus_one_is_square -l 80 -v\n"
            "  ake-scan examples/advanced_sentences.py predicate_sum_of_two_squares_equals_t -l 60 -v\n"
            "  ake-scan examples/advanced_sentences.py predicate_forall_a_exists_sqrt_one_plus_a_t -l 40 -q\n"
            "  ake-scan examples/advanced_sentences.py predicate_exists_even_valuation_nonsquare_ac -l 40 -q\n"
            "  ake-scan examples/advanced_sentences.py predicate_value_group_is_2_divisible -l 20\n"
            "  ake-scan examples/demo_hensel.py   # list predicates in a file\n"
        ),
    )
    parser.add_argument(
        "file_path",
        help="Path to the Python file containing the predicate function.",
    )
    parser.add_argument(
        "function_name",
        nargs="?",
        default=None,
        help=(
            "Predicate function (FieldFactory -> bool). "
            "Optional if the file defines exactly one; otherwise lists choices."
        ),
    )
    parser.add_argument(
        "-l",
        "--limit",
        type=int,
        default=50,
        help="Upper limit for primes to scan (default: 50).",
    )
    parser.add_argument(
        "-s",
        "--start",
        type=int,
        default=2,
        help="Lower bound for primes (default: 2).",
    )
    parser.add_argument(
        "--primes",
        type=_parse_primes,
        default=None,
        help="Comma-separated list of primes (overrides --start/--limit).",
    )
    parser.add_argument(
        "-p",
        "--precision",
        type=int,
        default=20,
        help="Laurent series precision (default: 20).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON report.",
    )
    parser.add_argument(
        "--csv",
        action="store_true",
        help="Emit per-prime CSV report.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Include failed/passed prime lists after the asymptotic summary.",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Include full detail (passed list, tail primes).",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress the 'Loading…/Scanning…' banner (summary only).",
    )
    parser.add_argument(
        "--progress",
        action="store_true",
        help="Print scan progress while running.",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        name, predicate = resolve_predicate(args.file_path, args.function_name)

        show_banner = (
            not args.json and not args.csv and not args.quiet
        )
        if show_banner:
            print(f"Loading '{name}' from '{args.file_path}'...")
            if args.primes:
                print(
                    f"Scanning primes {args.primes} with precision {args.precision}..."
                )
            else:
                print(
                    f"Scanning primes in [{args.start}, {args.limit}] "
                    f"with precision {args.precision}..."
                )

        results = scan_primes(
            predicate,
            prime_limit=None if args.primes else args.limit,
            precision=args.precision,
            start=args.start,
            primes=args.primes,
            progress=args.progress and not args.json and not args.csv,
        )

        if args.json:
            print(json.dumps(results_to_jsonable(results), indent=2))
        elif args.csv:
            print(format_csv_report(results), end="")
        else:
            if show_banner:
                print()
            print(
                format_text_report(
                    results,
                    verbose=args.verbose,
                    full=args.full,
                )
            )

        if results["error_count"] > 0:
            return 2
        return 0

    except SystemExit as e:
        # resolve_predicate uses SystemExit with a helpful multi-line message
        if isinstance(e.code, str):
            print(e.code, file=sys.stderr)
            return 1
        raise
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
