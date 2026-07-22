"""Structured pass/fail verdicts with optional witnesses and obstruction codes."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional, Union

from ake_scanner.algebra.laurent import LaurentSeries


# Common reason codes (stable strings for UI / JSON)
CODE_WITNESS = "witness"
CODE_ODD_VALUATION = "odd_valuation"
CODE_VALUATION_NOT_DIVISIBLE = "valuation_not_divisible"
CODE_NONSQUARE_RESIDUE = "nonsquare_residue"
CODE_NOT_NTH_POWER_RESIDUE = "not_nth_power_residue"
CODE_P_DIVIDES_N = "p_divides_n"
CODE_NO_LIFT = "no_lift_at_precision"
CODE_CHAR_2_OBSTRUCTION = "char_2_obstruction"
CODE_ALWAYS_FALSE = "always_false"
CODE_ALWAYS_TRUE = "always_true"
CODE_RESIDUE_CONDITION = "residue_condition"
CODE_RUNTIME = "runtime_error"
CODE_UNKNOWN_FAIL = "unknown_failure"


def series_to_witness(series: Optional[LaurentSeries], max_terms: int = 12) -> Optional[Dict[str, Any]]:
    """Serialize a Laurent series for JSON / UI (truncated coeff map)."""
    if series is None:
        return None
    if series.is_zero():
        return {
            "kind": "laurent",
            "prime": series.prime,
            "precision": series.precision,
            "valuation": None,
            "zero": True,
            "coeffs": {},
        }
    items = sorted(series.coeffs.items(), key=lambda kv: kv[0])
    if len(items) > max_terms:
        items = items[:max_terms]
        truncated = True
    else:
        truncated = False
    return {
        "kind": "laurent",
        "prime": series.prime,
        "precision": series.precision,
        "valuation": int(series.valuation),
        "zero": False,
        "coeffs": {str(d): int(c) for d, c in items},
        "truncated": truncated,
    }


@dataclass
class Verdict:
    """
    Outcome of evaluating a sentence at one prime.

    Predicates may return ``bool`` (legacy) or ``Verdict``. ``Verdict`` is
    truthy iff ``holds`` is true, so existing ``if pred(F):`` code still works.
    """

    holds: bool
    code: str
    message: str = ""
    witness: Optional[Dict[str, Any]] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return self.holds

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Drop empty meta for cleaner JSON
        if not d.get("meta"):
            d.pop("meta", None)
        if d.get("witness") is None:
            d.pop("witness", None)
        return d


def ok(
    message: str = "",
    *,
    code: str = CODE_WITNESS,
    witness: Optional[Dict[str, Any]] = None,
    series: Optional[LaurentSeries] = None,
    **meta: Any,
) -> Verdict:
    w = witness
    if w is None and series is not None:
        w = series_to_witness(series)
    return Verdict(True, code, message or "holds", witness=w, meta=dict(meta))


def fail(
    code: str,
    message: str = "",
    *,
    witness: Optional[Dict[str, Any]] = None,
    **meta: Any,
) -> Verdict:
    return Verdict(False, code, message or code, witness=witness, meta=dict(meta))


def coerce_verdict(value: Union[bool, Verdict, Any]) -> Verdict:
    """Normalize a predicate return value to a Verdict."""
    if isinstance(value, Verdict):
        return value
    if value is True:
        return ok("predicate returned True", code=CODE_ALWAYS_TRUE)
    if value is False:
        return fail(CODE_UNKNOWN_FAIL, "predicate returned False (no structured reason)")
    # Truthy/falsy fallback
    if value:
        return ok(f"truthy return ({type(value).__name__})", code=CODE_ALWAYS_TRUE)
    return fail(CODE_UNKNOWN_FAIL, f"falsy return ({type(value).__name__})")
