"""Truncated formal Laurent series over F_p.

Elements of F_p((t)) are represented with **absolute** truncation: coefficients
of degree > precision are discarded. Binary arithmetic uses
``min(self.precision, other.precision)``. Equality compares coefficients and
prime only (after truncation).

Precision guarantee for inverses
--------------------------------
For nonzero ``a`` with valuation ``v`` and precision ``P``,

    ``a * a.inv()`` equals ``1`` in every degree ``d`` with
    ``0 <= d <= P + min(0, v)``.

In particular, when ``v >= 0`` the product is exactly ``1`` up to absolute
degree ``P``. When ``v < 0``, absolute truncation of the inverse drops terms
that would cancel degrees near ``P``, so residuals may appear above
``P + v``. Prefer a larger ``precision`` (or nonnegative valuation) when this
matters.
"""

from __future__ import annotations

from typing import Dict, Optional, Union


class LaurentSeries:
    """
    An element of the field of formal Laurent series F_p((t)).

    Coefficients are stored as {degree: value mod p}, omitting zeros.
    Degrees above ``precision`` are truncated (absolute O(t^{precision+1})).
    """

    def __init__(self, coeffs: Dict[int, int], prime: int, precision: int = 20):
        if prime < 2:
            raise ValueError(f"prime must be >= 2, got {prime}")
        if precision < 0:
            raise ValueError(f"precision must be >= 0, got {precision}")

        self.prime = prime
        self.precision = precision
        self.coeffs: Dict[int, int] = {}
        for deg, val in coeffs.items():
            if deg > precision:
                continue
            v = val % prime
            if v != 0:
                self.coeffs[deg] = v

        self._valuation: Optional[int] = None

    # ------------------------------------------------------------------
    # Core properties
    # ------------------------------------------------------------------

    @property
    def valuation(self) -> Union[int, float]:
        if not self.coeffs:
            return float("inf")
        if self._valuation is None:
            self._valuation = min(self.coeffs.keys())
        return self._valuation

    def is_zero(self) -> bool:
        return not self.coeffs

    def __bool__(self) -> bool:
        return not self.is_zero()

    def leading_coefficient(self) -> int:
        """Coefficient of t^{val}. Returns 0 for the zero series."""
        if self.is_zero():
            return 0
        return self.coeffs[self.valuation]

    def unit_part(self) -> "LaurentSeries":
        """
        Write self = t^v * u with val(u) = 0; return u.

        The zero series has no unit part.
        """
        if self.is_zero():
            raise ZeroDivisionError("Zero series has no unit part")
        v = self.valuation
        return LaurentSeries(
            {d - v: c for d, c in self.coeffs.items()},
            self.prime,
            self.precision,
        )

    def residue(self) -> int:
        """
        Residue of the unit part in F_p (constant term after normalizing valuation).

        Equivalent to leading_coefficient() for nonzero series.
        """
        return self.leading_coefficient()

    def shift(self, k: int) -> "LaurentSeries":
        """Return self * t^k (multiply degrees by shifting)."""
        if self.is_zero():
            return LaurentSeries({}, self.prime, self.precision)
        return LaurentSeries(
            {d + k: c for d, c in self.coeffs.items()},
            self.prime,
            self.precision,
        )

    def with_precision(self, precision: int) -> "LaurentSeries":
        """Return a copy truncated (or padded in capacity) to the given precision."""
        return LaurentSeries(self.coeffs, self.prime, precision)

    def _require_same_prime(self, other: "LaurentSeries") -> None:
        if self.prime != other.prime:
            raise ValueError(
                f"Primes must match (got {self.prime} and {other.prime})"
            )

    def _op_precision(self, other: "LaurentSeries") -> int:
        return min(self.precision, other.precision)

    # ------------------------------------------------------------------
    # Arithmetic
    # ------------------------------------------------------------------

    def __add__(self, other: "LaurentSeries") -> "LaurentSeries":
        self._require_same_prime(other)
        prec = self._op_precision(other)
        new_coeffs = {
            d: c for d, c in self.coeffs.items() if d <= prec
        }
        for deg, val in other.coeffs.items():
            if deg > prec:
                continue
            new_coeffs[deg] = new_coeffs.get(deg, 0) + val
        return LaurentSeries(new_coeffs, self.prime, prec)

    def __sub__(self, other: "LaurentSeries") -> "LaurentSeries":
        self._require_same_prime(other)
        prec = self._op_precision(other)
        new_coeffs = {
            d: c for d, c in self.coeffs.items() if d <= prec
        }
        for deg, val in other.coeffs.items():
            if deg > prec:
                continue
            new_coeffs[deg] = new_coeffs.get(deg, 0) - val
        return LaurentSeries(new_coeffs, self.prime, prec)

    def __mul__(self, other: "LaurentSeries") -> "LaurentSeries":
        self._require_same_prime(other)
        prec = self._op_precision(other)
        if self.is_zero() or other.is_zero():
            return LaurentSeries({}, self.prime, prec)

        new_coeffs: Dict[int, int] = {}
        for d1, v1 in self.coeffs.items():
            for d2, v2 in other.coeffs.items():
                deg = d1 + d2
                if deg > prec:
                    continue
                new_coeffs[deg] = new_coeffs.get(deg, 0) + v1 * v2
        return LaurentSeries(new_coeffs, self.prime, prec)

    def __neg__(self) -> "LaurentSeries":
        return LaurentSeries(
            {d: -v for d, v in self.coeffs.items()},
            self.prime,
            self.precision,
        )

    def inv(self) -> "LaurentSeries":
        """
        Multiplicative inverse via term-by-term reciprocal of the unit part.

        If A = t^v * U with val(U) = 0, then A^{-1} = t^{-v} * U^{-1}.

        See module docstring for the absolute-precision product guarantee.
        """
        if self.is_zero():
            raise ZeroDivisionError("Cannot invert zero series")

        v = int(self.valuation)
        # Unit part: degrees relative to valuation
        u_coeffs = {d - v: val for d, val in self.coeffs.items()}

        a0 = u_coeffs[0]
        a0_inv = pow(a0, -1, self.prime)
        res_coeffs: Dict[int, int] = {0: a0_inv}

        # Final degree of unit-inverse term k is k - v. Keep k - v <= precision,
        # i.e. compute unit inverse through degree precision + v.
        limit_deg = self.precision + v
        if limit_deg < 0:
            # Only the leading term of the inverse survives absolute truncation.
            return LaurentSeries({-v: a0_inv}, self.prime, self.precision)

        for k in range(1, limit_deg + 1):
            sum_val = 0
            for i, a_val in u_coeffs.items():
                if i == 0 or i > k:
                    continue
                x_idx = k - i
                if x_idx in res_coeffs:
                    sum_val = (sum_val + a_val * res_coeffs[x_idx]) % self.prime

            val = (-a0_inv * sum_val) % self.prime
            if val != 0:
                res_coeffs[k] = val

        final_coeffs = {d - v: val for d, val in res_coeffs.items()}
        return LaurentSeries(final_coeffs, self.prime, self.precision)

    def inverse_product_safe_degree(self) -> int:
        """Largest degree at which ``self * self.inv()`` is guaranteed to be 1."""
        if self.is_zero():
            raise ZeroDivisionError("Zero series has no inverse")
        v = int(self.valuation)
        return self.precision + min(0, v)

    def __truediv__(self, other: "LaurentSeries") -> "LaurentSeries":
        return self * other.inv()

    def __rtruediv__(self, other: int) -> "LaurentSeries":
        # Allow scalar / series: n / self
        return LaurentSeries.constant(other, self.prime, self.precision) / self

    def __pow__(self, exp: int) -> "LaurentSeries":
        if not isinstance(exp, int):
            return NotImplemented
        if exp == 0:
            return LaurentSeries.constant(1, self.prime, self.precision)
        if exp < 0:
            return self.inv() ** (-exp)
        # Exponentiation by squaring
        result = LaurentSeries.constant(1, self.prime, self.precision)
        base = self
        e = exp
        while e > 0:
            if e & 1:
                result = result * base
            base = base * base
            e >>= 1
        return result

    # ------------------------------------------------------------------
    # Comparison / display
    # ------------------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, LaurentSeries):
            return NotImplemented
        return self.coeffs == other.coeffs and self.prime == other.prime

    def __repr__(self) -> str:
        if self.is_zero():
            return "0"
        terms = []
        for deg in sorted(self.coeffs.keys()):
            val = self.coeffs[deg]
            if deg == 0:
                terms.append(f"{val}")
            elif deg == 1:
                terms.append(f"{val}t")
            else:
                terms.append(f"{val}t^{deg}")
        return " + ".join(terms)

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @staticmethod
    def t(prime: int, precision: int = 20) -> "LaurentSeries":
        """Factory for the uniformizer t."""
        return LaurentSeries({1: 1}, prime, precision)

    @staticmethod
    def constant(value: int, prime: int, precision: int = 20) -> "LaurentSeries":
        """Factory for scalar constants in F_p ⊂ F_p((t))."""
        return LaurentSeries({0: value}, prime, precision)

    @staticmethod
    def zero(prime: int, precision: int = 20) -> "LaurentSeries":
        return LaurentSeries({}, prime, precision)

    @staticmethod
    def one(prime: int, precision: int = 20) -> "LaurentSeries":
        return LaurentSeries({0: 1}, prime, precision)
