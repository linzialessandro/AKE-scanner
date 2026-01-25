from typing import Dict, Union, Optional

class LaurentSeries:
    """
    Represents an element in the field of formal Laurent series F_p((t)).
    Coefficients are standard integers modulo p.
    """
    def __init__(self, coeffs: Dict[int, int], prime: int, precision: int = 20):
        self.prime = prime
        self.precision = precision
        self.precision = precision
        self.coeffs = {}
        for deg, val in coeffs.items():
            if deg > precision:
                continue
            v = val % prime
            if v != 0:
                self.coeffs[deg] = v
        
        self._valuation: Optional[int] = None
    
    @property
    def valuation(self) -> Union[int, float]:
        if not self.coeffs:
            return float('inf')
        if self._valuation is None:
            self._valuation = min(self.coeffs.keys())
        return self._valuation

    def is_zero(self) -> bool:
        return len(self.coeffs) == 0

    def __add__(self, other: 'LaurentSeries') -> 'LaurentSeries':
        if self.prime != other.prime:
            raise ValueError("Primes must match")
        
        new_coeffs = self.coeffs.copy()
        for deg, val in other.coeffs.items():
            new_coeffs[deg] = (new_coeffs.get(deg, 0) + val)
        
        return LaurentSeries(new_coeffs, self.prime, self.precision)

    def __sub__(self, other: 'LaurentSeries') -> 'LaurentSeries':
        if self.prime != other.prime:
            raise ValueError("Primes must match")
            
        new_coeffs = self.coeffs.copy()
        for deg, val in other.coeffs.items():
            new_coeffs[deg] = (new_coeffs.get(deg, 0) - val)
            
        return LaurentSeries(new_coeffs, self.prime, self.precision)

    def __mul__(self, other: 'LaurentSeries') -> 'LaurentSeries':
        if self.prime != other.prime:
            raise ValueError("Primes must match")
        
        if self.is_zero() or other.is_zero():
             return LaurentSeries({}, self.prime, self.precision)
             
        # Convolution
        new_coeffs = {}
        min_deg_self = self.valuation
        min_deg_other = other.valuation
        
        for d1, v1 in self.coeffs.items():
            for d2, v2 in other.coeffs.items():
                deg = d1 + d2
                if deg > self.precision:
                    continue
                new_coeffs[deg] = (new_coeffs.get(deg, 0) + v1 * v2)
        
        return LaurentSeries(new_coeffs, self.prime, self.precision)
    
    def __neg__(self) -> 'LaurentSeries':
        return LaurentSeries({d: -v for d, v in self.coeffs.items()}, self.prime, self.precision)

    def inv(self) -> 'LaurentSeries':
        """
        Computes multiplicative inverse.
        If A = t^v * U where U is a unit (val(U) = 0), then A^-1 = t^-v * U^-1.
        """
        if self.is_zero():
            raise ZeroDivisionError("Cannot invert zero series")
            
        v = self.valuation
        # Shift to make valuation 0
        u_coeffs = {d - v: val for d, val in self.coeffs.items()}
        
        # Newton iteration for U * X = 1
        # X_{k+1} = X_k * (2 - U * X_k)
        # We solve sum_{i=0}^k a_i x_{k-i} = 0 term-by-term.
        
        a0 = u_coeffs[0]
        a0_inv = pow(a0, -1, self.prime)
        res_coeffs = {}
        res_coeffs[0] = a0_inv
        
        limit_deg = self.precision + v
        
        for k in range(1, limit_deg + 20):
            if k > limit_deg:
                 break
            
            sum_val = 0
            for i, a_val in u_coeffs.items():
                if i == 0: continue
                if i > k: continue
                
                x_idx = k - i
                if x_idx in res_coeffs:
                    sum_val = (sum_val + a_val * res_coeffs[x_idx])
            
            const_term = -a0_inv * sum_val
            val = const_term % self.prime
            if val != 0:
                res_coeffs[k] = val
                
        # Shift back
        final_coeffs = {d - v: val for d, val in res_coeffs.items()}
        return LaurentSeries(final_coeffs, self.prime, self.precision)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, LaurentSeries):
            return NotImplemented
        return self.coeffs == other.coeffs and self.prime == other.prime

    def __repr__(self):
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

    @staticmethod
    def t(prime: int, precision: int = 20) -> 'LaurentSeries':
        """Factory for the variable t."""
        return LaurentSeries({1: 1}, prime, precision)
    
    @staticmethod
    def constant(value: int, prime: int, precision: int = 20) -> 'LaurentSeries':
        """Factory for scalar constants."""
        return LaurentSeries({0: value}, prime, precision)

