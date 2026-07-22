"""Non-trivial FO-style sentences for AKE scans (layer 2).

Three families beyond basic Hensel power equations:

1. **Simultaneous systems** — several unknowns / several equations at once
2. **Quantifier alternation** — constructive Π₁ / Π₂ / Σ₂ sketches over the
   finite residue field F_p (true ∀/∃ ranging over a finite set)
3. **Value group & angular component** — Denef–Pas style language fragments
   using ``v(·)`` and ``ac(·)`` on F_p((t))

Each ``predicate_*`` returns a structured :class:`~ake_scanner.logic.verdict.Verdict`
(witness / obstruction) when practical, still truthy as a bool for the scanner.

Run examples::

    ake-scan examples/advanced_sentences.py predicate_sum_of_two_squares_equals_t -l 60 -v
    ake-scan examples/advanced_sentences.py predicate_forall_a_exists_sqrt_one_plus_a_t -l 40 -q
    ake-scan examples/advanced_sentences.py predicate_exists_even_valuation_nonsquare_ac -l 40 -q
    ake-scan examples/advanced_sentences.py   # list all
"""

from __future__ import annotations

from typing import Optional, Tuple

from ake_scanner.logic.scanner import FieldFactory
from ake_scanner.logic.diagnose import diagnose_residue_square, diagnose_x_n_equals
from ake_scanner.logic.verdict import (
    CODE_ALWAYS_FALSE,
    CODE_ALWAYS_TRUE,
    CODE_CHAR_2_OBSTRUCTION,
    CODE_NO_LIFT,
    CODE_NONSQUARE_RESIDUE,
    CODE_RESIDUE_CONDITION,
    CODE_WITNESS,
    Verdict,
    fail,
    ok,
    series_to_witness,
)
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


def _diagnose_sum_of_two_squares(target: LaurentSeries, F: FieldFactory) -> Verdict:
    hit = _sum_of_two_squares_series(target, F)
    if hit is None:
        return fail(
            CODE_NO_LIFT,
            "no (x,y) found with x²+y² = target under low-degree ansatz",
            prime=F.prime,
        )
    x, y = hit
    return ok(
        "found x,y with x² + y² = target",
        code=CODE_WITNESS,
        witness={
            "kind": "pair",
            "x": series_to_witness(x),
            "y": series_to_witness(y),
        },
        prime=F.prime,
    )


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

def predicate_sum_of_two_squares_minus_one_residue(F: FieldFactory) -> Verdict:
    """Exists a, b in F_p with a² + b² = -1.

    Expected: always_true on scanned primes (true for every prime field).
    Simultaneous system over the residue field only.
    """
    if _is_sum_of_two_squares_mod_p(-1, F.prime):
        return ok(
            "exists a,b in F_p with a²+b² ≡ -1",
            code=CODE_RESIDUE_CONDITION,
            prime=F.prime,
        )
    return fail(CODE_ALWAYS_FALSE, "no representation of -1 as sum of two squares mod p", prime=F.prime)


def predicate_sum_of_two_squares_equals_one_plus_t(F: FieldFactory) -> Verdict:
    """Exists x, y in F_p((t)) with x² + y² = 1 + t.

    Expected: eventually_true; fails at p = 2.
    """
    return _diagnose_sum_of_two_squares(F.constant(1) + F.t, F)


def predicate_sum_of_two_squares_equals_t(F: FieldFactory) -> Verdict:
    """Exists x, y in F_p((t)) with x² + y² = t.

    Expected: mixed — leading-term cancellation is required (odd valuation).
    """
    return _diagnose_sum_of_two_squares(F.t, F)


def predicate_sum_of_two_squares_equals_minus_one(F: FieldFactory) -> Verdict:
    """Exists x, y in F_p((t)) with x² + y² = -1.

    Expected: always_true (constant solutions already exist in F_p ⊂ F_p((t))).
    """
    return _diagnose_sum_of_two_squares(F.constant(-1), F)


def predicate_independent_simultaneous_squares(F: FieldFactory) -> Verdict:
    """Exists x, y with x² = 1 + t and y² = 1 + 2 t  (independent equations).

    Expected: eventually_true; fails at p = 2.
    """
    vx = diagnose_x_n_equals(F.constant(1) + F.t, 2, F.precision)
    if not vx.holds:
        return fail(vx.code, f"x²=1+t fails: {vx.message}", prime=F.prime, part="x")
    vy = diagnose_x_n_equals(F.constant(1) + F.constant(2) * F.t, 2, F.precision)
    if not vy.holds:
        return fail(vy.code, f"y²=1+2t fails: {vy.message}", prime=F.prime, part="y")
    return ok(
        "independent square roots for 1+t and 1+2t",
        witness={"kind": "pair", "x": vx.witness, "y": vy.witness},
        prime=F.prime,
    )


def predicate_simultaneous_i_and_sqrt_one_plus_t(F: FieldFactory) -> Verdict:
    """Exists x, y with x² = -1 and y² = 1 + t.

    Expected: mixed — needs −1 square in F_p (p ≡ 1 mod 4) and the Hensel
    square root of 1 + t (fails at p = 2).
    """
    vi = diagnose_residue_square(-1, F.prime, label="-1")
    if not vi.holds:
        return fail(vi.code, f"no i in F_p: {vi.message}", prime=F.prime)
    vs = diagnose_x_n_equals(F.constant(1) + F.t, 2, F.precision)
    if not vs.holds:
        return fail(vs.code, f"no √(1+t): {vs.message}", prime=F.prime)
    return ok(
        "both −1 square and √(1+t)",
        witness={"kind": "pair", "i": vi.witness, "sqrt": vs.witness},
        prime=F.prime,
    )


def predicate_pythagorean_unit_circle(F: FieldFactory) -> Verdict:
    """Exists x, y with x² + y² = 1.

    Expected: always_true (e.g. (1, 0); or many other residue points).
    """
    return _diagnose_sum_of_two_squares(F.constant(1), F)


def predicate_simultaneous_product_and_sum(F: FieldFactory) -> Verdict:
    """Exists x, y with x y = 1 and x + y = 3  (roots of T² − 3T + 1 = 0).

    Expected: mixed / eventually_true depending on discriminant 5 being square
    in F_p (and p ≠ 2 for characteristic issues).
    """
    p = F.prime
    for x in range(p):
        if x == 0:
            continue
        y = pow(x, -1, p)
        if (x + y) % p == 3 % p:
            return ok(
                f"residue solution x={x}, y={y}",
                code=CODE_RESIDUE_CONDITION,
                witness={"kind": "residue_pair", "x": x, "y": y, "prime": p},
                prime=p,
            )
    return fail(
        CODE_NONSQUARE_RESIDUE,
        "no residue roots of T² − 3T + 1 (disc 5 not square / char issues)",
        prime=p,
    )


# ===========================================================================
# 2. Quantifier alternation (constructive, ∀ ranges over finite F_p)
# ===========================================================================

def predicate_forall_a_exists_sqrt_one_plus_a_t(F: FieldFactory) -> Verdict:
    """∀ a ∈ F_p  ∃ x ∈ F_p((t))  such that x² = 1 + a t.

    Expected: eventually_true; fails at p = 2.
    """
    p, prec = F.prime, F.precision
    for a in range(p):
        target = F.constant(1) + F.constant(a) * F.t
        v = diagnose_x_n_equals(target, 2, prec)
        if not v.holds:
            return fail(
                v.code,
                f"fails for a={a}: {v.message}",
                prime=p,
                bad_a=a,
            )
    return ok(f"√(1+a t) exists for all a in F_{p}", code=CODE_WITNESS, prime=p)


def predicate_forall_nonzero_square_a_exists_sqrt_a_plus_t(
    F: FieldFactory,
) -> Verdict:
    """∀ a ∈ F_p^* (a square)  ∃ x  with x² = a + t.

    Expected: eventually_true; fails at p = 2.
    """
    p, prec = F.prime, F.precision
    if p == 2:
        v = diagnose_x_n_equals(F.constant(1) + F.t, 2, prec)
        if v.holds:
            return ok("p=2 special case 1+t", series=None, prime=2)
        return fail(v.code, v.message, prime=2)
    for a in range(1, p):
        if not is_quadratic_residue(a, p):
            continue
        v = diagnose_x_n_equals(F.constant(a) + F.t, 2, prec)
        if not v.holds:
            return fail(v.code, f"fails for square a={a}: {v.message}", prime=p, bad_a=a)
    return ok("√(a+t) for every nonzero square a", code=CODE_WITNESS, prime=p)


def predicate_exists_nonsquare_forall_not_square(F: FieldFactory) -> Verdict:
    """∃ c ∈ F_p  ∀ a ∈ F_p  (a² ≠ c)   — existence of a quadratic non-residue.

    Expected: eventually_true; fails at p = 2.
    """
    p = F.prime
    c = _find_nonsquare(p)
    if c is None:
        return fail(
            CODE_CHAR_2_OBSTRUCTION if p == 2 else CODE_ALWAYS_FALSE,
            f"no quadratic non-residue in F_{p}",
            prime=p,
        )
    return ok(
        f"nonsquare c={c} in F_{p}",
        code=CODE_RESIDUE_CONDITION,
        witness={"kind": "residue", "value": c, "prime": p},
        prime=p,
    )


def predicate_forall_a_exists_artin_schreier_preimage(F: FieldFactory) -> Verdict:
    """∀ a ∈ F_p  ∃ b ∈ F_p  such that b² − b = a.

    Expected: always_false. The Artin–Schreier map is not surjective.
    """
    p = F.prime
    image = {(b * b - b) % p for b in range(p)}
    missing = [a for a in range(p) if a not in image]
    if not missing:
        return ok("Artin–Schreier surjective (unexpected for odd p)", prime=p)
    return fail(
        CODE_ALWAYS_FALSE,
        f"Artin–Schreier image size {len(image)}/{p}; missing e.g. a={missing[0]}",
        prime=p,
        image_size=len(image),
        missing_sample=missing[0],
    )


def predicate_forall_a_quadratic_T2_aT_1_splits(F: FieldFactory) -> Verdict:
    """∀ a ∈ F_p  ∃ r ∈ F_p  with r² + a r + 1 = 0.

    Expected: eventually_false (only tiny p may pass).
    """
    p = F.prime
    for a in range(p):
        disc = (a * a - 4) % p
        if not is_quadratic_residue(disc, p):
            return fail(
                CODE_NONSQUARE_RESIDUE,
                f"disc a²-4 not square for a={a} (disc={disc})",
                prime=p,
                bad_a=a,
                disc=disc,
            )
    return ok("T²+aT+1 splits for every a", code=CODE_RESIDUE_CONDITION, prime=p)


def predicate_exists_uniform_square_root_base(F: FieldFactory) -> Verdict:
    """∃ u unit  such that  ∀ a ∈ F_p  ∃ x  with x² = u + a t.

    Expected: eventually_true; witness u = 1.
    """
    candidates = [1]
    ns = _find_nonsquare(F.prime)
    if ns is not None:
        candidates.append(ns)
    for c in candidates:
        ok_all = True
        for a in range(F.prime):
            target = F.constant(c) + F.constant(a) * F.t
            if solve_x_n_equals(target, 2, F.precision) is None:
                ok_all = False
                break
        if ok_all:
            return ok(
                f"uniform base u={c} works for all a",
                code=CODE_WITNESS,
                witness={"kind": "residue", "value": c, "prime": F.prime},
                prime=F.prime,
                u=c,
            )
    return fail(CODE_NO_LIFT, "no tested unit base works for all a", prime=F.prime)


def predicate_forall_val_in_window_even_of_squares(F: FieldFactory) -> Verdict:
    """∀ k ∈ [-M, M]  ( ∃ x  v(x) = k  ∧  x is a square  ⇒  k even ).

    Expected: always_true.
    """
    M = 8
    for k in range(-M, M + 1):
        if k % 2 == 0:
            continue
        target = F.t ** k if k >= 0 else F.element({k: 1})
        v = diagnose_x_n_equals(target, 2, F.precision)
        if v.holds:
            return fail(
                CODE_ALWAYS_FALSE,
                f"odd valuation k={k} admitted a square (unexpected)",
                prime=F.prime,
                k=k,
            )
    return ok(
        "odd valuations in window are never squares",
        code=CODE_ALWAYS_TRUE,
        prime=F.prime,
    )


# ===========================================================================
# 3. Value group (v) and angular component (ac)
# ===========================================================================

def predicate_exists_uniformizer_ac_one(F: FieldFactory) -> Verdict:
    """Exists π with v(π) = 1 and ac(π) = 1.

    Expected: always_true (witness π = t).
    """
    pi = F.t
    if _val(pi) == 1 and _ac(pi) == 1:
        return ok("π = t", series=pi, prime=F.prime)
    return fail(CODE_ALWAYS_FALSE, "t is not a uniformizer with ac=1", prime=F.prime)


def predicate_exists_element_valuation_one(F: FieldFactory) -> Verdict:
    """Exists x with v(x) = 1.

    Expected: always_true.
    """
    if _val(F.t) == 1:
        return ok("v(t)=1", series=F.t, prime=F.prime)
    return fail(CODE_ALWAYS_FALSE, "v(t)≠1", prime=F.prime)


def predicate_exists_val_one_with_nonsquare_ac(F: FieldFactory) -> Verdict:
    """Exists x with v(x) = 1 and ac(x) a quadratic non-residue.

    Expected: eventually_true; fails at p = 2.
    """
    c = _find_nonsquare(F.prime)
    if c is None:
        return fail(
            CODE_CHAR_2_OBSTRUCTION if F.prime == 2 else CODE_ALWAYS_FALSE,
            f"no nonsquare in F_{F.prime}",
            prime=F.prime,
        )
    x = F.constant(c) * F.t
    if _val(x) == 1 and not is_quadratic_residue(_ac(x), F.prime):
        return ok(f"x = {c}·t", series=x, prime=F.prime, ac=c)
    return fail(CODE_NO_LIFT, "constructed x failed v/ac checks", prime=F.prime)


def predicate_exists_even_valuation_nonsquare_ac(F: FieldFactory) -> Verdict:
    """Exists x with v(x) even, ac(x) nonsquare — hence x is not a square.

    Expected: eventually_true; fails at p = 2.
    """
    c = _find_nonsquare(F.prime)
    if c is None:
        return fail(
            CODE_CHAR_2_OBSTRUCTION if F.prime == 2 else CODE_ALWAYS_FALSE,
            f"no nonsquare in F_{F.prime}",
            prime=F.prime,
        )
    x = F.constant(c) * (F.t ** 2)
    if _val(x) is None or _val(x) % 2 != 0:
        return fail(CODE_NO_LIFT, "valuation not even", prime=F.prime)
    if is_quadratic_residue(_ac(x), F.prime):
        return fail(CODE_NO_LIFT, "ac unexpectedly square", prime=F.prime)
    v = diagnose_x_n_equals(x, 2, F.precision)
    if v.holds:
        return fail(CODE_ALWAYS_FALSE, "x was a series square (unexpected)", prime=F.prime)
    return ok(
        f"x={c}·t² has even v, nonsquare ac, not a series square",
        series=x,
        prime=F.prime,
        obstruction=v.code,
    )


def predicate_value_group_is_2_divisible(F: FieldFactory) -> Verdict:
    """∀ k ∈ [-M,M] ∃ y  with v(y²) = k   (value group 2-divisible).

    Expected: always_false for Γ ≅ ℤ (odd k have no half).
    """
    M = 6
    for k in range(-M, M + 1):
        if k % 2 != 0:
            return fail(
                CODE_ALWAYS_FALSE,
                f"value group ℤ is not 2-divisible: no half of k={k}",
                prime=F.prime,
                odd_k=k,
            )
        m = k // 2
        y = F.t ** m if m >= 0 else F.element({m: 1})
        if _val(y * y) != k:
            return fail(CODE_ALWAYS_FALSE, f"v(y²)≠k for k={k}", prime=F.prime)
    return ok("window 2-divisible (unexpected for ℤ)", prime=F.prime)


def predicate_ultrametric_cancellation(F: FieldFactory) -> Verdict:
    """Exists x, y with v(x) = v(y) and v(x + y) > v(x).

    Expected: always_true (witness x = 1, y = -1).
    """
    x = F.constant(1)
    y = F.constant(-1)
    s = x + y
    vx, vy = _val(x), _val(y)
    if vx is None or vy is None or vx != vy:
        return fail(CODE_ALWAYS_FALSE, "v(1)≠v(-1)", prime=F.prime)
    if s.is_zero() or (_val(s) is not None and _val(s) > vx):
        return ok(
            "x=1, y=-1: strict triangle / cancellation",
            code=CODE_ALWAYS_TRUE,
            prime=F.prime,
        )
    return fail(CODE_ALWAYS_FALSE, "no cancellation for 1+(-1)", prime=F.prime)


def predicate_ac_multiplicative_on_samples(F: FieldFactory) -> Verdict:
    """∀ samples x, y ≠ 0: ac(x y) = ac(x) ac(y) in F_p.

    Expected: always_true.
    """
    p = F.prime
    samples = [
        F.t,
        F.constant(1) + F.t,
        F.constant(2 % p) if p > 2 else F.constant(1),
        F.constant(1) / (F.constant(1) + F.t),
        F.element({-1: 1}),
        F.constant(3 % p) * (F.t ** 2) if p > 3 else F.t ** 2,
    ]
    nonzero = [s for s in samples if not s.is_zero()]
    for x in nonzero:
        for y in nonzero:
            lhs = _ac(x * y)
            rhs = (_ac(x) * _ac(y)) % p
            if lhs != rhs:
                return fail(
                    CODE_ALWAYS_FALSE,
                    f"ac not multiplicative: ac(xy)={lhs} ≠ {rhs}",
                    prime=p,
                )
    return ok("ac multiplicative on sample set", code=CODE_ALWAYS_TRUE, prime=p)


def predicate_ac_of_one_plus_t_is_one(F: FieldFactory) -> Verdict:
    """ac(1 + t) = 1.

    Expected: always_true.
    """
    ac = _ac(F.constant(1) + F.t)
    if ac == 1 % F.prime:
        return ok("ac(1+t)=1", code=CODE_ALWAYS_TRUE, prime=F.prime, ac=ac)
    return fail(CODE_ALWAYS_FALSE, f"ac(1+t)={ac}", prime=F.prime, ac=ac)


def predicate_square_implies_even_val_and_square_ac(F: FieldFactory) -> Verdict:
    """∀ constructed squares s = z²: v(s) even ∧ ac(s) square.

    Expected: always_true.
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
            return fail(CODE_ALWAYS_FALSE, f"v(z²) not even for sample z", prime=p)
        if not is_quadratic_residue(_ac(s), p):
            return fail(CODE_ALWAYS_FALSE, "ac(z²) not square", prime=p)
    return ok("squares have even v and square ac on samples", code=CODE_ALWAYS_TRUE, prime=p)


def predicate_exists_unit_nonsquare_ac_not_series_square(F: FieldFactory) -> Verdict:
    """Exists unit u with ac(u) nonsquare (hence u not a square in F_p((t))).

    Expected: eventually_true; fails at p = 2.
    """
    c = _find_nonsquare(F.prime)
    if c is None:
        return fail(
            CODE_CHAR_2_OBSTRUCTION if F.prime == 2 else CODE_ALWAYS_FALSE,
            f"no nonsquare in F_{F.prime}",
            prime=F.prime,
        )
    u = F.constant(c)
    v = diagnose_x_n_equals(u, 2, F.precision)
    if _val(u) == 0 and not is_quadratic_residue(_ac(u), F.prime) and not v.holds:
        return ok(f"unit u={c} nonsquare ac, not a series square", series=u, prime=F.prime)
    return fail(CODE_NO_LIFT, "unit nonsquare certificate failed", prime=F.prime)


def predicate_valuation_of_frobenius_gap(F: FieldFactory) -> Verdict:
    """Exists x with v(x) < 0 and v(x^p − x) = p · v(x).

    Expected: always_true. Witness x = t^{-1}.
    """
    x = F.element({-1: 1})
    k = _val(x)
    if k is None or k >= 0:
        return fail(CODE_ALWAYS_FALSE, "v(t^{-1}) not negative", prime=F.prime)
    xp = x ** F.prime
    diff = xp - x
    if _val(diff) == F.prime * k:
        return ok(
            f"v(x^p−x)=p·v(x) for x=t^{{-1}} (k={k})",
            code=CODE_ALWAYS_TRUE,
            series=x,
            prime=F.prime,
        )
    return fail(
        CODE_ALWAYS_FALSE,
        f"v(x^p−x)={_val(diff)} ≠ {F.prime * k}",
        prime=F.prime,
    )


def predicate_compatible_v_ac_square_criterion_on_units(F: FieldFactory) -> Verdict:
    """Constant series c is a square in F_p((t)) iff c is a square in F_p.

    Expected: always_true.
    """
    p, prec = F.prime, F.precision
    for c in range(1, p):
        v = diagnose_x_n_equals(F.constant(c), 2, prec)
        residue_says = is_quadratic_residue(c, p)
        if v.holds != residue_says:
            return fail(
                CODE_ALWAYS_FALSE,
                f"mismatch for c={c}: solver={v.holds} residue={residue_says}",
                prime=p,
                c=c,
            )
    return ok(
        "unit square criterion matches residue squares",
        code=CODE_ALWAYS_TRUE,
        prime=p,
    )
