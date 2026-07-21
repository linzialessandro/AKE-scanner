"""Reference predicates for AKE-style scans.

Uses the library Hensel/Newton solvers constructively.
"""

from ake_scanner.logic.scanner import FieldFactory
from ake_scanner.algebra.hensel import sqrt_series, nth_root, solve_x_n_equals


def solve_sqrt(target, precision: int = 20) -> bool:
    """
    True iff a square root of ``target`` exists (constructed via Newton/Hensel).
    Kept for backward compatibility with earlier demos.
    """
    root = sqrt_series(target, precision)
    return root is not None


def predicate_one_plus_t_is_square(F: FieldFactory) -> bool:
    """Exists x in F_p((t)) such that x^2 = 1 + t."""
    one_plus_t = F.constant(1) + F.t
    return solve_x_n_equals(one_plus_t, 2, F.precision) is not None


def predicate_t_is_square(F: FieldFactory) -> bool:
    """Exists x such that x^2 = t (false: odd valuation)."""
    return solve_x_n_equals(F.t, 2, F.precision) is not None


def predicate_one_plus_t_is_cube(F: FieldFactory) -> bool:
    """Exists x such that x^3 = 1 + t (fails when p | 3, i.e. p = 3)."""
    one_plus_t = F.constant(1) + F.t
    return solve_x_n_equals(one_plus_t, 3, F.precision) is not None
