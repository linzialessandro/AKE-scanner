"""Constructive diagnosis helpers for common sentence shapes."""

from __future__ import annotations

from typing import Optional

from ake_scanner.algebra.hensel import (
    is_quadratic_residue,
    nth_root,
    nth_root_mod_p,
    solve_x_n_equals,
    sqrt_mod_p,
    sqrt_series,
)
from ake_scanner.algebra.laurent import LaurentSeries
from ake_scanner.logic.verdict import (
    CODE_CHAR_2_OBSTRUCTION,
    CODE_NO_LIFT,
    CODE_NONSQUARE_RESIDUE,
    CODE_NOT_NTH_POWER_RESIDUE,
    CODE_ODD_VALUATION,
    CODE_P_DIVIDES_N,
    CODE_RESIDUE_CONDITION,
    CODE_VALUATION_NOT_DIVISIBLE,
    CODE_WITNESS,
    Verdict,
    fail,
    ok,
)


def diagnose_x_n_equals(
    target: LaurentSeries,
    n: int,
    precision: Optional[int] = None,
) -> Verdict:
    """
    Diagnose whether ``x^n = target`` has a constructive solution.

    Reports valuation / residue / characteristic obstructions when possible,
    otherwise the Newton/Hensel witness or a soft no-lift failure.
    """
    if precision is None:
        precision = target.precision
    target = target.with_precision(precision)
    p = target.prime

    if target.is_zero():
        if n > 0:
            return ok(
                "x = 0 is an n-th root of 0",
                series=LaurentSeries.zero(p, precision),
            )
        return fail(CODE_NO_LIFT, "zero target with non-positive n")

    val = int(target.valuation)

    # Valuation first (including char 2): odd v is never a square.
    if val % n != 0:
        if n == 2:
            return fail(
                CODE_ODD_VALUATION,
                f"valuation v = {val} is odd — not a square",
                n=n,
                valuation=val,
                prime=p,
            )
        return fail(
            CODE_VALUATION_NOT_DIVISIBLE,
            f"valuation v = {val} is not divisible by n = {n}",
            n=n,
            valuation=val,
            prime=p,
        )

    if n == 2 and p == 2:
        # Delegate to sqrt_series (char-2 square support rules on units)
        root = sqrt_series(target, precision)
        if root is not None:
            return ok(
                "square root via char-2 rules / Newton",
                series=root,
                n=2,
                valuation=val,
            )
        return fail(
            CODE_CHAR_2_OBSTRUCTION,
            "no square root in characteristic 2 at this precision "
            "(support / unit obstruction)",
            n=2,
            valuation=val,
            prime=p,
        )

    if n > 1 and n % p == 0:
        return fail(
            CODE_P_DIVIDES_N,
            f"p = {p} divides n = {n}; Newton derivative n x^{{n-1}} vanishes "
            "(standard Hensel step blocked)",
            n=n,
            prime=p,
            valuation=val,
        )

    lead = target.leading_coefficient()
    root_c = nth_root_mod_p(lead, n, p)
    if root_c is None:
        if n == 2:
            return fail(
                CODE_NONSQUARE_RESIDUE,
                f"leading coefficient {lead} is not a square in F_{p}",
                n=n,
                leading=lead,
                prime=p,
                valuation=val,
            )
        return fail(
            CODE_NOT_NTH_POWER_RESIDUE,
            f"leading coefficient {lead} is not an n-th power in F_{p} (n={n})",
            n=n,
            leading=lead,
            prime=p,
            valuation=val,
        )

    root = solve_x_n_equals(target, n, precision)
    if root is None:
        return fail(
            CODE_NO_LIFT,
            f"residue is an n-th power and valuation is divisible by n, "
            f"but no lift was constructed at precision {precision}",
            n=n,
            leading=lead,
            residue_root=root_c,
            prime=p,
            valuation=val,
            precision=precision,
        )

    return ok(
        f"constructed x with x^{n} = target (v={val}, ac root={root_c})",
        code=CODE_WITNESS,
        series=root,
        n=n,
        valuation=val,
        leading=lead,
        residue_root=root_c,
        prime=p,
    )


def diagnose_residue_square(a: int, prime: int, label: str = "a") -> Verdict:
    """Diagnose whether ``a`` is a square in F_p (residue field)."""
    a_mod = a % prime
    if prime == 2:
        return ok(
            f"{label} ≡ {a_mod} is a square in F_2",
            code=CODE_RESIDUE_CONDITION,
            witness={"kind": "residue", "value": a_mod, "root": a_mod, "prime": 2},
            prime=2,
            residue=a_mod,
        )
    if is_quadratic_residue(a_mod, prime):
        root = sqrt_mod_p(a_mod, prime)
        return ok(
            f"{label} ≡ {a_mod} is a square in F_{prime}"
            + (f" (root {root})" if root is not None else ""),
            code=CODE_RESIDUE_CONDITION,
            witness={
                "kind": "residue",
                "value": a_mod,
                "root": root,
                "prime": prime,
            },
            prime=prime,
            residue=a_mod,
            root=root,
        )
    return fail(
        CODE_NONSQUARE_RESIDUE,
        f"{label} ≡ {a_mod} is not a square in F_{prime} "
        f"(e.g. Legendre condition fails)",
        prime=prime,
        residue=a_mod,
    )
