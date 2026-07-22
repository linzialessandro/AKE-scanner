"""Command-line interface for AKE Scanner."""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from ake_scanner.logic.primes import is_prime
from ake_scanner.logic.scanner import results_to_jsonable, scan_primes
from ake_scanner.predicates import (
    list_predicates,
    load_module,
    load_predicate_from_file,
    resolve_predicate,
)
from ake_scanner.reporting import format_csv_report, format_text_report

# Stable re-exports for tests / older imports from ake_scanner.cli
_load_module = load_module
__all__ = [
    "main",
    "build_parser",
    "format_text_report",
    "format_csv_report",
    "list_predicates",
    "load_predicate_from_file",
    "resolve_predicate",
]


def _parse_primes(s: str) -> List[int]:
    parts = [p.strip() for p in s.split(",") if p.strip()]
    primes = []
    for part in parts:
        n = int(part)
        if not is_prime(n):
            raise argparse.ArgumentTypeError(f"{n} is not prime")
        primes.append(n)
    return primes


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
    parser.add_argument(
        "--explain",
        action="store_true",
        help=(
            "Record structured per-prime explanations (witness / obstruction codes). "
            "Always on when predicates return Verdict objects; this flag also "
            "forces explanation capture for bare bool predicates and prints them."
        ),
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
            explain=args.explain,
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
                    verbose=args.verbose or args.explain,
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
