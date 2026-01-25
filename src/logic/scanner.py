from typing import Callable, List, Dict, Any
import math
from src.algebra.laurent import LaurentSeries

class FieldFactory:
    """
    Passed to the user's predicate function.
    Allows creating elements in the field F_p((t)).
    """
    def __init__(self, prime: int, precision: int):
        self.prime = prime
        self.precision = precision
        
    @property
    def t(self) -> LaurentSeries:
        return LaurentSeries.t(self.prime, self.precision)
        
    def constant(self, n: int) -> LaurentSeries:
        return LaurentSeries.constant(n, self.prime, self.precision)
        
    def element(self, coeffs: Dict[int, int]) -> LaurentSeries:
        return LaurentSeries(coeffs, self.prime, self.precision)

def is_prime(n: int) -> bool:
    if n <= 1: return False
    if n <= 3: return True
    if n % 2 == 0 or n % 3 == 0: return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True

def generate_primes(limit: int):
    """Yields primes up to limit."""
    yield 2
    for n in range(3, limit + 1, 2):
        if is_prime(n):
            yield n

def scan_primes(predicate: Callable[[FieldFactory], bool], prime_limit: int, precision: int = 20) -> Dict[str, Any]:
    """
    Runs the predicate against F_p((t)) for all primes <= prime_limit.
    Returns a report of checks.
    """
    results = {
        'verified_count': 0,
        'failed_primes': [],
        'passed_primes': [],
        'details': {}
    }
    
    for p in generate_primes(prime_limit):
        factory = FieldFactory(p, precision)
        try:
            is_valid = predicate(factory)
            if is_valid:
                results['verified_count'] += 1
                results['passed_primes'].append(p)
            else:
                results['failed_primes'].append(p)
        except Exception as e:
            results['details'][p] = str(e)
            results['failed_primes'].append(p)
            
    return results
