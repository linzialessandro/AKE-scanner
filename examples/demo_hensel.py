"""Reference predicates for AKE-style scans.

Each ``predicate_*`` is a first-order style sentence encoded as
``FieldFactory -> bool``, checked *constructively* (Hensel/Newton witnesses
or explicit obstruction certificates) rather than by hardcoding prime sets.

Run examples::

    ake-scan examples/demo_hensel.py predicate_one_plus_t_is_square -l 50 -q
    ake-scan examples/demo_hensel.py predicate_minus_one_is_square -l 80 -v
    ake-scan examples/demo_hensel.py predicate_x_cubed_minus_x_equals_t -l 40 -q
"""

from __future__ import annotations

from ake_scanner.logic.scanner import FieldFactory
from ake_scanner.logic.diagnose import diagnose_residue_square, diagnose_x_n_equals
from ake_scanner.logic.verdict import Verdict
from ake_scanner.algebra.laurent import LaurentSeries
from ake_scanner.algebra.hensel import (
    sqrt_series,
    nth_root,
    solve_x_n_equals,
    is_quadratic_residue,
    has_root_via_hensel,
    hensel_lift,
)


# ---------------------------------------------------------------------------
# Classical Hensel demos (power equations x^n = 1 + t, etc.)
# ---------------------------------------------------------------------------

def solve_sqrt(target, precision: int = 20) -> bool:
    """
    True iff a square root of ``target`` exists (constructed via Newton/Hensel).
    Kept for backward compatibility with earlier demos.
    """
    root = sqrt_series(target, precision)
    return root is not None


def predicate_one_plus_t_is_square(F: FieldFactory) -> Verdict:
    """Exists x in F_p((t)) such that x^2 = 1 + t.

    Expected: eventually_true; exceptional prime p = 2.
    Returns a structured :class:`Verdict` (witness or obstruction code).
    """
    return diagnose_x_n_equals(F.constant(1) + F.t, 2, F.precision)


def predicate_t_is_square(F: FieldFactory) -> Verdict:
    """Exists x such that x^2 = t.

    Expected: always_false (valuation obstruction: v(t) = 1 is odd).
    """
    return diagnose_x_n_equals(F.t, 2, F.precision)


def predicate_one_plus_t_is_cube(F: FieldFactory) -> Verdict:
    """Exists x such that x^3 = 1 + t.

    Expected: eventually_true; fails when p | 3, i.e. p = 3
    (Newton derivative n x^{n-1} vanishes).
    """
    return diagnose_x_n_equals(F.constant(1) + F.t, 3, F.precision)


def predicate_one_plus_t_is_fifth_power(F: FieldFactory) -> Verdict:
    """Exists x such that x^5 = 1 + t.

    Expected: eventually_true; exceptional prime p = 5 (p | n blocks lift).
    """
    return diagnose_x_n_equals(F.constant(1) + F.t, 5, F.precision)


def predicate_one_plus_two_t_is_fourth_power(F: FieldFactory) -> Verdict:
    """Exists x such that x^4 = 1 + 2 t.

    Expected: eventually_true; fails at p = 2 (p | 4). Leading residue 1 is
    always a fourth power in F_p, so no further residue obstruction.
    """
    target = F.constant(1) + F.constant(2) * F.t
    return diagnose_x_n_equals(target, 4, F.precision)


def predicate_one_plus_t_plus_t_squared_is_square(F: FieldFactory) -> Verdict:
    """Exists x such that x^2 = 1 + t + t^2.

    Expected: eventually_true; fails at p = 2 (char-2 square support rules).
    A slightly richer unit than 1 + t.
    """
    target = F.constant(1) + F.t + F.t * F.t
    return diagnose_x_n_equals(target, 2, F.precision)


def predicate_one_over_one_plus_t_is_square(F: FieldFactory) -> Verdict:
    """Exists x such that x^2 = 1 / (1 + t)  (equivalently x^2 (1 + t) = 1).

    Expected: eventually_true; fails at p = 2.
    """
    inv = F.constant(1) / (F.constant(1) + F.t)
    return diagnose_x_n_equals(inv, 2, F.precision)


def predicate_t_squared_is_square(F: FieldFactory) -> Verdict:
    """Exists x such that x^2 = t^2.

    Expected: always_true (witness x = t; even valuation, residue 1).
    Control sentence with no arithmetic obstruction.
    """
    return diagnose_x_n_equals(F.t * F.t, 2, F.precision)


def predicate_one_plus_t_inv_squared_is_square(F: FieldFactory) -> Verdict:
    """Exists x such that x^2 = 1 + t^{-2}.

    Expected: always_true for scanned primes. Valuation -2 is even; after
    factoring t^{-2} the unit is 1 + t^2, which is a square via Hensel for
    all primes (including char 2: support of squares).
    """
    # 1 + t^{-2} = t^{-2} (t^2 + 1)
    target = F.constant(1) + F.element({-2: 1})
    return diagnose_x_n_equals(target, 2, F.precision)


# ---------------------------------------------------------------------------
# Residue-field conditions (mixed asymptotic patterns)
# ---------------------------------------------------------------------------

def predicate_minus_one_is_square(F: FieldFactory) -> Verdict:
    """Exists a in F_p with a^2 = -1  (Euler criterion on the residue field).

    Expected: mixed — true for p = 2 and p ≡ 1 (mod 4), false for p ≡ 3 (mod 4).
    Classic example where AKE reports no single threshold N.
    """
    return diagnose_residue_square(-1, F.prime, label="-1")


def predicate_two_is_square(F: FieldFactory) -> Verdict:
    """Exists a in F_p with a^2 = 2.

    Expected: mixed — true for p = 2 and p ≡ ±1 (mod 8).
    """
    return diagnose_residue_square(2, F.prime, label="2")


def predicate_minus_one_and_two_are_squares(F: FieldFactory) -> bool:
    """Exists a, b in F_p with a^2 = -1 and b^2 = 2.

    Expected: mixed — equivalent to p = 2 or p ≡ 1 (mod 8) among odd primes
    (intersection of the previous two conditions). Sparser than either alone.
    """
    return is_quadratic_residue(-1, F.prime) and is_quadratic_residue(2, F.prime)


def predicate_x_squared_plus_one(F: FieldFactory) -> bool:
    """Exists x in F_p[[t]] with x^2 + 1 = 0.

    Expected: mixed — same arithmetic as ``predicate_minus_one_is_square``,
    but witnessed by Hensel lifting a simple root of X^2 + 1 over F_p.
    (At p = 2 the residual root is multiple yet exact: x = 1 works.)
    """
    return has_root_via_hensel([1, 0, 1], F.prime, F.precision)


def predicate_primitive_cube_root_of_unity(F: FieldFactory) -> bool:
    """Exists x in F_p[[t]] with x^2 + x + 1 = 0 (primitive cube roots of 1).

    Expected: mixed — true when 3 | (p - 1), i.e. p ≡ 1 (mod 3), plus the
    degenerate case p = 3 (polynomial becomes (x - 1)^2 over F_3? actually
    x^2+x+1 = (x^3-1)/(x-1); at p=3, x^2+x+1 has discriminant -3=0, double
    root). Empirically fails at p = 2 and at p ≡ 2 (mod 3).
    """
    return has_root_via_hensel([1, 1, 1], F.prime, F.precision)


# ---------------------------------------------------------------------------
# Perturbed / non-constant polynomials and obstruction certificates
# ---------------------------------------------------------------------------

def predicate_x_cubed_minus_x_equals_t(F: FieldFactory) -> bool:
    """Exists x in F_p[[t]] with x^3 - x = t  (i.e. x^3 - x - t = 0).

    Expected: always_true on scanned primes. Residual polynomial X^3 - X
    factors as X(X-1)(X+1); at least one simple root has f' = 3x^2 - 1 ≠ 0
    for every p, so Newton lifts a root of the t-perturbation.
    """
    p, prec = F.prime, F.precision
    # coeffs of a0 + a1 x + a2 x^2 + a3 x^3 = -t - x + x^3
    coeffs = [
        -F.t,
        F.constant(-1),
        F.zero(),
        F.constant(1),
    ]
    residual_roots = [0, 1]
    if p > 2:
        residual_roots.append(p - 1)  # -1
    for r in residual_roots:
        # f'(x) = 3x^2 - 1
        deriv = (3 * (r * r) - 1) % p
        if deriv == 0:
            continue
        x0 = LaurentSeries.constant(r, p, prec)
        if hensel_lift(coeffs, x0, prec) is not None:
            return True
    return False


def predicate_artin_schreier_valuation_obstruction(F: FieldFactory) -> bool:
    """Exists x with x^p - x = t^{-1}.

    Expected: always_false. Valuation certificate (no search needed):

    - If v(x) ≥ 0 then v(x^p - x) ≥ 0 ≠ -1.
    - If v(x) = k < 0 then v(x^p) = p k < k = v(x), so v(x^p - x) = p k.
      Solving p k = -1 for integer k is impossible (p does not divide 1).

    This is an Artin–Schreier style obstruction visible already at the level
    of valuations on F_p((t)).
    """
    rhs_val = -1
    # Exhaust a bounded window of candidate valuations; the obstruction is
    # independent of the window size (p k = -1 never holds for integer k).
    for k in range(-40, 40):
        if k >= 0:
            # LHS valuation ≥ 0, cannot equal -1 as a precise leading term.
            if 0 == rhs_val:
                return True
        else:
            if F.prime * k == rhs_val:
                return True
    return False


def predicate_odd_valuation_never_a_square(F: FieldFactory) -> bool:
    """Exists x with x^2 = t^3  (valuation 3, odd).

    Expected: always_false. Companion to ``predicate_t_is_square`` with a
    higher odd valuation.
    """
    return solve_x_n_equals(F.t ** 3, 2, F.precision) is not None


def predicate_quadratic_with_parameter(F: FieldFactory) -> bool:
    """Exists x with x^2 = 1 + t + 2 t^3.

    Expected: eventually_true; fails at p = 2. Non-monomial unit; still a
    square once the leading residue is a square (here 1).
    """
    target = F.constant(1) + F.t + F.constant(2) * (F.t ** 3)
    return solve_x_n_equals(target, 2, F.precision) is not None
