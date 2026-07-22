"""Non-trivial FO-style sentences for AKE scans (layer 2).

Three families beyond basic Hensel power equations:

1. **Simultaneous systems** — several unknowns / several equations at once
2. **Quantifier alternation** — constructive Π₁ / Π₂ / Σ₂ sketches over the
   finite residue field F_p (true ∀/∃ ranging over a finite set)
3. **Value group & angular component** — Denef–Pas style language fragments
   using ``v(·)`` and ``ac(·)`` on F_p((t))

Each ``predicate_*`` is ``FieldFactory -> bool`` and builds witnesses (or
obstruction certificates) rather than hardcoding prime lists.

Run examples::

    ake-scan examples/advanced_sentences.py predicate_sum_of_two_squares_equals_t -l 60 -v
    ake-scan examples/advanced_sentences.py predicate_forall_a_exists_sqrt_one_plus_a_t -l 40 -q
    ake-scan examples/advanced_sentences.py predicate_exists_even_valuation_nonsquare_ac -l 40 -q
    ake-scan examples/advanced_sentences.py   # list all
"""

from __future__ import annotations

from typing import Optional, Tuple

from ake_scanner.logic.scanner import FieldFactory
from ake_scanner.algebra.laurent import LaurentSeries
from ake_scanner.algebra.hensel import (
    solve_x_n_equals,
    is_quadratic_residue,
)


# ---------------------------------------------------------------------------
# Shared constructive helpers
# ---------------------------------------------------------------------------

def _ac(series: LaurentSeries) -> int:
    """Angular component: leading coefficient in F_p (0 for the zero series)."""
    if series.is_zero():
        return 0
    return int(series.leading_coefficient()) % series.prime


def _val(series: LaurentSeries) -> Optional[int]:
    """Valuation in ℤ, or None for the zero series (v=∞)."""
    if series.is_zero():
        return None
    return int(series.valuation)


def _sum_of_two_squares_series(
    target: LaurentSeries, F: FieldFactory
) -> Optional[Tuple[LaurentSeries, LaurentSeries]]:
    """
    Search for x, y with x² + y² = target.

    Strategy: try y in a low-degree ansatz (constants, then degree-1), and
    solve for x via Newton square roots. Sufficient for the demo targets.
    """
    p, prec = F.prime, F.precision
    target = target.with_precision(prec)

    def try_y(y: LaurentSeries) -> Optional[Tuple[LaurentSeries, LaurentSeries]]:
        diff = target - y * y
        x = solve_x_n_equals(diff, 2, prec)
        if x is not None:
            return x, y
        return None

    for b in range(p):
        hit = try_y(F.constant(b))
        if hit is not None:
            return hit
    for b in range(p):
        for c in range(1, p):
            hit = try_y(F.constant(b) + F.constant(c) * F.t)
            if hit is not None:
                return hit
    return None


def _is_sum_of_two_squares_mod_p(a: int, p: int) -> bool:
    """Exists x, y in F_p with x² + y² ≡ a (mod p)."""
    a %= p
    for x in range(p):
        x2 = (x * x) % p
        for y in range(p):
            if (x2 + (y * y) % p) % p == a:
                return True
    return False


def _find_nonsquare(p: int) -> Optional[int]:
    """One quadratic non-residue in F_p^*, or None if every unit is a square."""
    for c in range(1, p):
        if not is_quadratic_residue(c, p):
            return c
    return None


# ===========================================================================
# 1. Simultaneous systems
# ===========================================================================

def predicate_sum_of_two_squares_minus_one_residue(F: FieldFactory) -> bool:
    """Exists a, b in F_p with a² + b² = -1.

    Expected: always_true on scanned primes (true for every prime field).
    Simultaneous system over the residue field only.
    """
    return _is_sum_of_two_squares_mod_p(-1, F.prime)


def predicate_sum_of_two_squares_equals_one_plus_t(F: FieldFactory) -> bool:
    """Exists x, y in F_p((t)) with x² + y² = 1 + t.

    Expected: eventually_true; fails at p = 2.
    Witness search: fix low-degree y, Newton-solve for x.
    """
    return _sum_of_two_squares_series(F.constant(1) + F.t, F) is not None


def predicate_sum_of_two_squares_equals_t(F: FieldFactory) -> bool:
    """Exists x, y in F_p((t)) with x² + y² = t.

    Expected: mixed — leading-term cancellation is required (odd valuation).
    With the ansatz y ∈ F_p, this needs t − b² to be a square; b = 1 works
    when −1 is a square in F_p, i.e. roughly p = 2 or p ≡ 1 (mod 4)
    (p = 2 fails for independent char-2 reasons in the solver).
    """
    return _sum_of_two_squares_series(F.t, F) is not None


def predicate_sum_of_two_squares_equals_minus_one(F: FieldFactory) -> bool:
    """Exists x, y in F_p((t)) with x² + y² = -1.

    Expected: always_true (constant solutions already exist in F_p ⊂ F_p((t))).
    """
    return _sum_of_two_squares_series(F.constant(-1), F) is not None


def predicate_independent_simultaneous_squares(F: FieldFactory) -> bool:
    """Exists x, y with x² = 1 + t and y² = 1 + 2 t  (independent equations).

    Expected: eventually_true; fails at p = 2.
    Conjunction of two constructive existential checks.
    """
    ok_x = solve_x_n_equals(F.constant(1) + F.t, 2, F.precision) is not None
    ok_y = (
        solve_x_n_equals(F.constant(1) + F.constant(2) * F.t, 2, F.precision)
        is not None
    )
    return ok_x and ok_y


def predicate_simultaneous_i_and_sqrt_one_plus_t(F: FieldFactory) -> bool:
    """Exists x, y with x² = -1 and y² = 1 + t.

    Expected: mixed — needs −1 square in F_p (p ≡ 1 mod 4) and the Hensel
    square root of 1 + t (fails at p = 2). Intersection of a residue condition
    with a series condition.
    """
    has_i = is_quadratic_residue(-1, F.prime)
    has_sqrt = (
        solve_x_n_equals(F.constant(1) + F.t, 2, F.precision) is not None
    )
    return has_i and has_sqrt


def predicate_pythagorean_unit_circle(F: FieldFactory) -> bool:
    """Exists x, y with x² + y² = 1.

    Expected: always_true (e.g. (1, 0); or many other residue points).
    """
    return _sum_of_two_squares_series(F.constant(1), F) is not None


def predicate_simultaneous_product_and_sum(F: FieldFactory) -> bool:
    """Exists x, y with x y = 1 and x + y = 3  (roots of T² − 3T + 1 = 0).

    Expected: mixed / eventually_true depending on discriminant 5 being square
    in F_p (and p ≠ 2 for characteristic issues). Constructive: search residue
    roots of T² − 3T + 1, which are already solutions in F_p ⊂ F_p((t)).
    """
    p = F.prime
    for x in range(p):
        if x == 0:
            continue
        # y = x^{-1}, require x + y ≡ 3
        y = pow(x, -1, p)
        if (x + y) % p == 3 % p:
            return True
    return False


# ===========================================================================
# 2. Quantifier alternation (constructive, ∀ ranges over finite F_p)
# ===========================================================================

def predicate_forall_a_exists_sqrt_one_plus_a_t(F: FieldFactory) -> bool:
    """∀ a ∈ F_p  ∃ x ∈ F_p((t))  such that x² = 1 + a t.

    Expected: eventually_true; fails at p = 2.
    Π₂ sketch: outer universal quantifier is finite (residue field).
    """
    p, prec = F.prime, F.precision
    for a in range(p):
        target = F.constant(1) + F.constant(a) * F.t
        if solve_x_n_equals(target, 2, prec) is None:
            return False
    return True


def predicate_forall_nonzero_square_a_exists_sqrt_a_plus_t(
    F: FieldFactory,
) -> bool:
    """∀ a ∈ F_p^* (a square)  ∃ x  with x² = a + t.

    Expected: eventually_true; fails at p = 2.
    Restricted universal quantifier over quadratic residues.
    """
    p, prec = F.prime, F.precision
    if p == 2:
        return solve_x_n_equals(F.constant(1) + F.t, 2, prec) is not None
    for a in range(1, p):
        if not is_quadratic_residue(a, p):
            continue
        if solve_x_n_equals(F.constant(a) + F.t, 2, prec) is None:
            return False
    return True


def predicate_exists_nonsquare_forall_not_square(F: FieldFactory) -> bool:
    """∃ c ∈ F_p  ∀ a ∈ F_p  (a² ≠ c)   — existence of a quadratic non-residue.

    Expected: eventually_true; fails at p = 2 (every element of F_2 is a square).
    Σ₂ sketch with a finite universal matrix.
    """
    p = F.prime
    for c in range(p):
        if all((a * a) % p != c % p for a in range(p)):
            return True
    return False


def predicate_forall_a_exists_artin_schreier_preimage(F: FieldFactory) -> bool:
    """∀ a ∈ F_p  ∃ b ∈ F_p  such that b² − b = a.

    Expected: always_false. The Artin–Schreier map ℘(b) = b² − b on F_p is
    2-to-1 onto a proper subgroup of index 2 when p is odd (image size
    (p+1)/2); not surjective. Checked by exhausting the finite field.
    """
    p = F.prime
    image = {(b * b - b) % p for b in range(p)}
    return all(a in image for a in range(p))


def predicate_forall_a_quadratic_T2_aT_1_splits(F: FieldFactory) -> bool:
    """∀ a ∈ F_p  ∃ r ∈ F_p  with r² + a r + 1 = 0.

    Expected: eventually_false (only tiny p may pass). Equivalent to
    disc(a) = a² − 4 being a square for every a — false for all odd p ≥ 3.
    """
    p = F.prime
    for a in range(p):
        disc = (a * a - 4) % p
        if not is_quadratic_residue(disc, p):
            return False
    return True


def predicate_exists_uniform_square_root_base(F: FieldFactory) -> bool:
    """∃ u unit  such that  ∀ a ∈ F_p  ∃ x  with x² = u + a t.

    Expected: eventually_true; witness u = 1 (reduces to the Π₂ sentence
    ``predicate_forall_a_exists_sqrt_one_plus_a_t``). Σ₂ / ∃∀∃ sketch.
    """
    # Try a few explicit unit candidates constructively
    candidates = [1]
    ns = _find_nonsquare(F.prime)
    if ns is not None:
        candidates.append(ns)
    for c in candidates:
        ok = True
        for a in range(F.prime):
            target = F.constant(c) + F.constant(a) * F.t
            if solve_x_n_equals(target, 2, F.precision) is None:
                ok = False
                break
        if ok:
            return True
    return False


def predicate_forall_val_in_window_even_of_squares(F: FieldFactory) -> bool:
    """∀ k ∈ [-M, M]  ( ∃ x  v(x) = k  ∧  x is a square  ⇒  k even ).

    Expected: always_true. Contrapositive check: for odd k, every series of
    valuation k fails to be a square (solver returns None). Finite Π₁ over a
    window of the value group.
    """
    M = 8
    for k in range(-M, M + 1):
        if k % 2 == 0:
            continue
        # Representative of valuation k: t^k
        target = F.t ** k if k >= 0 else F.element({k: 1})
        if solve_x_n_equals(target, 2, F.precision) is not None:
            return False
    return True


# ===========================================================================
# 3. Value group (v) and angular component (ac)
# ===========================================================================

def predicate_exists_uniformizer_ac_one(F: FieldFactory) -> bool:
    """Exists π with v(π) = 1 and ac(π) = 1.

    Expected: always_true (witness π = t).
    """
    pi = F.t
    return _val(pi) == 1 and _ac(pi) == 1


def predicate_exists_element_valuation_one(F: FieldFactory) -> bool:
    """Exists x with v(x) = 1  (value group is nontrivial / has generator class).

    Expected: always_true.
    """
    return _val(F.t) == 1


def predicate_exists_val_one_with_nonsquare_ac(F: FieldFactory) -> bool:
    """Exists x with v(x) = 1 and ac(x) a quadratic non-residue.

    Expected: eventually_true; fails at p = 2 (no nonsquare in F_2).
    Witness x = c · t for nonsquare c.
    """
    c = _find_nonsquare(F.prime)
    if c is None:
        return False
    x = F.constant(c) * F.t
    return _val(x) == 1 and not is_quadratic_residue(_ac(x), F.prime)


def predicate_exists_even_valuation_nonsquare_ac(F: FieldFactory) -> bool:
    """Exists x with v(x) even, ac(x) nonsquare — hence x is not a square.

    Expected: eventually_true; fails at p = 2.
    Witness x = c · t²; solver confirms non-square.
    """
    c = _find_nonsquare(F.prime)
    if c is None:
        return False
    x = F.constant(c) * (F.t ** 2)
    if _val(x) % 2 != 0:
        return False
    if is_quadratic_residue(_ac(x), F.prime):
        return False
    return solve_x_n_equals(x, 2, F.precision) is None


def predicate_value_group_is_2_divisible(F: FieldFactory) -> bool:
    """∀ k ∈ [-M,M] ∃ y  with v(y²) = k   (i.e. the value group is 2-divisible).

    Expected: always_false for Γ ≅ ℤ (odd k have no half). Finite window
    check over the ordered group language.
    """
    M = 6
    for k in range(-M, M + 1):
        # Exists integer m with 2m = k?
        if k % 2 != 0:
            return False
        # Witness y = t^{k/2}
        m = k // 2
        y = F.t ** m if m >= 0 else F.element({m: 1})
        if _val(y * y) != k:
            return False
    return True


def predicate_ultrametric_cancellation(F: FieldFactory) -> bool:
    """Exists x, y with v(x) = v(y) and v(x + y) > v(x).

    Expected: always_true (witness x = 1, y = -1; strict triangle inequality).
    """
    x = F.constant(1)
    y = F.constant(-1)
    s = x + y
    vx, vy = _val(x), _val(y)
    if vx is None or vy is None or vx != vy:
        return False
    if s.is_zero():
        return True  # v = ∞ > v(x)
    return _val(s) > vx


def predicate_ac_multiplicative_on_samples(F: FieldFactory) -> bool:
    """∀ samples x, y ≠ 0 in a finite test set: ac(x y) = ac(x) ac(y) in F_p.

    Expected: always_true. Angular component is a multiplicative map
    K^* → k^*; checked on an explicit finite set of Laurent monomials/units.
    """
    p = F.prime
    samples = [
        F.t,
        F.constant(1) + F.t,
        F.constant(2 % p) if p > 2 else F.constant(1),
        F.constant(1) / (F.constant(1) + F.t),
        F.element({-1: 1}),  # t^{-1}
        F.constant(3 % p) * (F.t ** 2) if p > 3 else F.t ** 2,
    ]
    nonzero = [s for s in samples if not s.is_zero()]
    for x in nonzero:
        for y in nonzero:
            lhs = _ac(x * y)
            rhs = (_ac(x) * _ac(y)) % p
            if lhs != rhs:
                return False
    return True


def predicate_ac_of_one_plus_t_is_one(F: FieldFactory) -> bool:
    """ac(1 + t) = 1.

    Expected: always_true. Basic angular-component computation on a fixed term.
    """
    return _ac(F.constant(1) + F.t) == 1 % F.prime


def predicate_square_implies_even_val_and_square_ac(F: FieldFactory) -> bool:
    """∀ constructed squares s = z² (z in a finite set): v(s) even ∧ ac(s) square.

    Expected: always_true. Necessity of the two square conditions in the
    (v, ac) language — verified on witnesses rather than the full field.
    """
    p = F.prime
    generators = [
        F.constant(1),
        F.constant(1) + F.t,
        F.t,
        F.constant(2 % p) + F.t if p > 2 else F.t,
        F.element({-1: 1}) + F.constant(1),
    ]
    for z in generators:
        if z.is_zero():
            continue
        s = z * z
        v = _val(s)
        if v is None or v % 2 != 0:
            return False
        if not is_quadratic_residue(_ac(s), p):
            return False
    return True


def predicate_exists_unit_nonsquare_ac_not_series_square(F: FieldFactory) -> bool:
    """Exists unit u with ac(u) nonsquare (hence u not a square in F_p((t))).

    Expected: eventually_true; fails at p = 2.
    """
    c = _find_nonsquare(F.prime)
    if c is None:
        return False
    u = F.constant(c)
    return (
        _val(u) == 0
        and not is_quadratic_residue(_ac(u), F.prime)
        and solve_x_n_equals(u, 2, F.precision) is None
    )


def predicate_valuation_of_frobenius_gap(F: FieldFactory) -> bool:
    """Exists x with v(x) < 0 and v(x^p − x) = p · v(x).

    Expected: always_true for all primes. If v(x) = k < 0 then
    v(x^p) = p k < k = v(x), so no cancellation and v(x^p − x) = p k.
    Witness x = t^{-1}.
    """
    x = F.element({-1: 1})
    k = _val(x)
    if k is None or k >= 0:
        return False
    # In characteristic p, (t^{-1})^p = t^{-p}; minus t^{-1} has val -p
    # Build x^p via repeated multiplication (integer power).
    xp = x ** F.prime
    diff = xp - x
    return _val(diff) == F.prime * k


def predicate_compatible_v_ac_square_criterion_on_units(F: FieldFactory) -> bool:
    """For every unit residue c ∈ F_p^*, the constant series c is a square in
    F_p((t)) iff c is a square in F_p  (v=0 already even).

    Expected: always_true. Links ac-criterion to the Hensel solver on constants.
    """
    p, prec = F.prime, F.precision
    for c in range(1, p):
        series = F.constant(c)
        solver_says = solve_x_n_equals(series, 2, prec) is not None
        residue_says = is_quadratic_residue(c, p)
        if solver_says != residue_says:
            return False
    return True
