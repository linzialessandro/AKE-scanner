"""Constructive solvers for existential statements in F_p((t)).

Provides Hensel/Newton lifting and power-residue helpers so predicates can
*build* witnesses rather than hardcoding number-theoretic answers.
"""

from __future__ import annotations

from typing import List, Optional, Sequence

from ake_scanner.algebra.laurent import LaurentSeries


# ---------------------------------------------------------------------------
# Finite-field helpers (residue field F_p)
# ---------------------------------------------------------------------------

def is_quadratic_residue(a: int, p: int) -> bool:
    """True iff a is a square in F_p (including 0)."""
    a %= p
    if a == 0:
        return True
    if p == 2:
        return True  # F_2: 0 and 1 are both squares
    return pow(a, (p - 1) // 2, p) == 1


def sqrt_mod_p(a: int, p: int) -> Optional[int]:
    """Return one square root of a in F_p, or None if none exists."""
    a %= p
    if a == 0:
        return 0
    if p == 2:
        return a
    if not is_quadratic_residue(a, p):
        return None
    # Brute force is fine for research-scale primes; Tonelli–Shanks optional later
    for x in range(1, p):
        if (x * x) % p == a:
            return x
    return None


def nth_root_mod_p(a: int, n: int, p: int) -> Optional[int]:
    """Return one n-th root of a in F_p, or None."""
    if n <= 0:
        raise ValueError("n must be positive")
    a %= p
    if a == 0:
        return 0
    if p == 2:
        return a  # only nonzero element is 1
    for x in range(1, p):
        if pow(x, n, p) == a:
            return x
    return None


# ---------------------------------------------------------------------------
# Series power checks / roots
# ---------------------------------------------------------------------------

def is_square_char_2(series: LaurentSeries) -> bool:
    """
    In F_2((t)), the Frobenius is x |-> x^2 and image consists of series
    whose support lies only on even degrees.
    """
    if series.prime != 2:
        raise ValueError("is_square_char_2 requires prime 2")
    if series.is_zero():
        return True
    return all(d % 2 == 0 for d in series.coeffs)


def sqrt_series(target: LaurentSeries, precision: Optional[int] = None) -> Optional[LaurentSeries]:
    """
    Attempt to compute a square root of ``target`` in F_p((t)).

    Returns a series x with x^2 ≈ target up to precision, or None if no
    square root exists (odd valuation, non-residue leading coefficient, or
    char-2 obstruction).
    """
    if precision is None:
        precision = target.precision
    target = target.with_precision(precision)

    if target.is_zero():
        return LaurentSeries.zero(target.prime, precision)

    p = target.prime
    val = int(target.valuation)

    if val % 2 != 0:
        return None

    if p == 2:
        if not is_square_char_2(target):
            return None
        # Constructive sqrt in char 2: sqrt(sum a_i t^{2i}) = sum a_i t^i
        # (since a_i in {0,1} and Frobenius is identity on F_2)
        half = {d // 2: c for d, c in target.coeffs.items()}
        return LaurentSeries(half, 2, precision)

    # Normalize: target = t^{2k} * u, val(u)=0
    base = target.leading_coefficient()
    root_c = sqrt_mod_p(base, p)
    if root_c is None:
        return None

    k = val // 2
    u = target.unit_part().with_precision(precision)

    # Newton: x <- (x + u/x) / 2, start from constant root_c
    inv_2 = LaurentSeries.constant(pow(2, -1, p), p, precision)
    x = LaurentSeries.constant(root_c, p, precision)

    # Doubling precision each step; log2(precision)+2 iterations suffice
    iterations = max(6, precision.bit_length() + 2)
    try:
        for _ in range(iterations):
            x_new = (x + u / x) * inv_2
            if x_new == x:
                break
            x = x_new
    except ZeroDivisionError:
        return None

    # Verify x^2 ≈ u inside a safe window
    diff = (x * x) - u
    if not diff.is_zero() and int(diff.valuation) <= precision - 2:
        return None

    return x.shift(k)


def is_nth_power(series: LaurentSeries, n: int, precision: Optional[int] = None) -> bool:
    """Return True if ``series`` is an n-th power in F_p((t)) (constructively)."""
    return nth_root(series, n, precision) is not None


def nth_root(
    series: LaurentSeries, n: int, precision: Optional[int] = None
) -> Optional[LaurentSeries]:
    """
    Compute an n-th root of ``series`` when it exists as a simple Hensel lift.

    Conditions (char does not divide n, or handled specially for n=2, char 2):
    - valuation divisible by n
    - leading coefficient is an n-th power in F_p
    - derivative of x^n - u is invertible at the lift (i.e. p does not divide n
      when lifting units, for n > 1)
    """
    if n <= 0:
        raise ValueError("n must be positive")
    if n == 1:
        return series if precision is None else series.with_precision(precision)
    if n == 2:
        return sqrt_series(series, precision)

    if precision is None:
        precision = series.precision
    series = series.with_precision(precision)

    if series.is_zero():
        return LaurentSeries.zero(series.prime, precision)

    p = series.prime
    val = int(series.valuation)
    if val % n != 0:
        return None

    # p | n blocks the standard Newton step for units (f' = n x^{n-1} = 0)
    if n % p == 0:
        # Decline wild ramification / inseparable case for now
        return None

    base = series.leading_coefficient()
    root_c = nth_root_mod_p(base, n, p)
    if root_c is None:
        return None

    k = val // n
    u = series.unit_part().with_precision(precision)
    x = LaurentSeries.constant(root_c, p, precision)

    # Newton for f(x) = x^n - u:  x <- x - f(x)/f'(x) = ((n-1)x + u/x^{n-1}) / n
    inv_n = LaurentSeries.constant(pow(n, -1, p), p, precision)
    n_minus_1 = LaurentSeries.constant(n - 1, p, precision)

    iterations = max(6, precision.bit_length() + 2)
    try:
        for _ in range(iterations):
            x_pow = x ** (n - 1)
            x_new = (n_minus_1 * x + u / x_pow) * inv_n
            if x_new == x:
                break
            x = x_new
    except ZeroDivisionError:
        return None

    diff = (x ** n) - u
    if not diff.is_zero() and int(diff.valuation) <= precision - 2:
        return None

    return x.shift(k)


# ---------------------------------------------------------------------------
# General univariate Hensel lift over F_p[[t]]
# ---------------------------------------------------------------------------

def eval_poly(
    coeffs: Sequence[LaurentSeries], x: LaurentSeries
) -> LaurentSeries:
    """Evaluate polynomial sum coeffs[i] * x^i (Horner)."""
    if not coeffs:
        return LaurentSeries.zero(x.prime, x.precision)
    result = coeffs[-1]
    for c in reversed(coeffs[:-1]):
        result = result * x + c
    return result


def eval_poly_derivative(
    coeffs: Sequence[LaurentSeries], x: LaurentSeries
) -> LaurentSeries:
    """Evaluate derivative of sum coeffs[i] * x^i."""
    if len(coeffs) < 2:
        return LaurentSeries.zero(x.prime, x.precision)
    # sum i * coeffs[i] * x^{i-1}
    p = x.prime
    prec = x.precision
    result = LaurentSeries.zero(p, prec)
    x_pow = LaurentSeries.one(p, prec)
    for i in range(1, len(coeffs)):
        term = coeffs[i] * x_pow * LaurentSeries.constant(i % p, p, prec)
        result = result + term
        x_pow = x_pow * x
    return result


def hensel_lift(
    coeffs: Sequence[LaurentSeries],
    x0: LaurentSeries,
    precision: Optional[int] = None,
    max_iterations: Optional[int] = None,
) -> Optional[LaurentSeries]:
    """
    Lift a simple root of f(x) = sum coeffs[i] x^i using Newton iteration.

    Requires f'(x0) to be a unit (valuation 0) so the step is valid.
    ``x0`` is typically a constant in F_p that is a simple root of the residual
    polynomial. Returns a root to the given precision, or None on failure.
    """
    if not coeffs:
        raise ValueError("polynomial coefficients required")
    p = coeffs[0].prime
    if precision is None:
        precision = min(c.precision for c in coeffs)
        precision = min(precision, x0.precision)

    coeffs = [c.with_precision(precision) for c in coeffs]
    x = x0.with_precision(precision)

    # Check derivative is invertible at the start
    fp = eval_poly_derivative(coeffs, x)
    if fp.is_zero() or int(fp.valuation) != 0:
        return None

    if max_iterations is None:
        max_iterations = max(8, precision.bit_length() + 3)

    try:
        for _ in range(max_iterations):
            fx = eval_poly(coeffs, x)
            if fx.is_zero() or int(fx.valuation) > precision - 1:
                return x
            fpx = eval_poly_derivative(coeffs, x)
            if fpx.is_zero() or int(fpx.valuation) != 0:
                return None
            x = x - fx / fpx
    except ZeroDivisionError:
        return None

    fx = eval_poly(coeffs, x)
    if fx.is_zero() or int(fx.valuation) > precision - 2:
        return x
    return None


def find_residue_roots_of_integer_poly(
    int_coeffs: Sequence[int], p: int
) -> List[int]:
    """
    Find roots in F_p of a polynomial with integer coefficients
    (constant ... highest degree), reduced mod p.
    """
    roots = []
    for x in range(p):
        acc = 0
        pow_x = 1
        for c in int_coeffs:
            acc = (acc + (c % p) * pow_x) % p
            pow_x = (pow_x * x) % p
        if acc == 0:
            roots.append(x)
    return roots


def has_root_via_hensel(
    int_coeffs: Sequence[int],
    prime: int,
    precision: int,
    series_coeffs: Optional[Sequence[Optional[LaurentSeries]]] = None,
) -> bool:
    """
    Check existence of a root in F_p[[t]] (or F_p((t))) for a polynomial that
    reduces to an integer polynomial mod t.

    ``int_coeffs`` are coefficients of f in F_p[x] (the residual polynomial).
    If ``series_coeffs`` is provided, those are the full F_p[[t]] coefficients;
    otherwise int_coeffs are treated as constant series.
    """
    if series_coeffs is None:
        coeffs = [
            LaurentSeries.constant(c, prime, precision) for c in int_coeffs
        ]
    else:
        coeffs = list(series_coeffs)

    for r in find_residue_roots_of_integer_poly(int_coeffs, prime):
        x0 = LaurentSeries.constant(r, prime, precision)
        # Exact constant root (covers multiple roots of t-independent polys)
        fx0 = eval_poly(coeffs, x0)
        if fx0.is_zero():
            return True
        # Simple root: f'(r) != 0 in F_p, lift via Newton
        deriv = 0
        for i in range(1, len(int_coeffs)):
            deriv = (
                deriv
                + (i % prime) * (int_coeffs[i] % prime) * pow(r, i - 1, prime)
            ) % prime
        if deriv == 0:
            continue
        if hensel_lift(coeffs, x0, precision) is not None:
            return True
    return False


def solve_x_n_equals(
    target: LaurentSeries, n: int, precision: Optional[int] = None
) -> Optional[LaurentSeries]:
    """Solve x^n = target; convenience wrapper around nth_root."""
    return nth_root(target, n, precision)
