"""Prime generation and list normalization for the scanner."""

from __future__ import annotations

from typing import List, Optional, Sequence


def is_prime(n: int) -> bool:
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True


def generate_primes(limit: int, start: int = 2):
    """Yield primes in [start, limit]."""
    if limit < 2 or start > limit:
        return
    begin = max(2, start)
    if begin <= 2 <= limit:
        yield 2
        begin = 3
    if begin % 2 == 0:
        begin += 1
    for n in range(begin, limit + 1, 2):
        if is_prime(n):
            yield n


def sieve_primes(limit: int, start: int = 2) -> List[int]:
    """Return all primes in [start, limit] via the sieve of Eratosthenes."""
    if limit < 2:
        return []
    sieve = bytearray(b"\x01") * (limit + 1)
    sieve[0:2] = b"\x00\x00"
    for i in range(2, int(limit**0.5) + 1):
        if sieve[i]:
            step = i
            start_mul = i * i
            sieve[start_mul : limit + 1 : step] = b"\x00" * (
                ((limit - start_mul) // step) + 1
            )
    begin = max(2, start)
    return [i for i in range(begin, limit + 1) if sieve[i]]


def normalize_prime_list(
    prime_limit: Optional[int],
    start: int,
    primes: Optional[Sequence[int]],
) -> List[int]:
    """Return a sorted list of primes to scan from either an explicit list or a range."""
    if primes is not None:
        return sorted({p for p in primes if is_prime(p) and p >= start})
    if prime_limit is None:
        raise ValueError("Either prime_limit or primes must be provided")
    if prime_limit <= 10_000:
        return list(generate_primes(prime_limit, start=start))
    return sieve_primes(prime_limit, start=start)


# Back-compat alias used by older call sites
_normalize_prime_list = normalize_prime_list
