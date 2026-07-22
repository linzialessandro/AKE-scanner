"""Tonelli–Shanks and large-prime square roots in F_p."""

import unittest

import _pathsetup  # noqa: F401
from ake_scanner.algebra.hensel import is_quadratic_residue, sqrt_mod_p, nth_root_mod_p


def _is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    i = 3
    while i * i <= n:
        if n % i == 0:
            return False
        i += 2
    return True


class TestTonelliShanks(unittest.TestCase):
    def test_small_primes_match_definition(self):
        for p in [3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 97]:
            for a in range(p):
                r = sqrt_mod_p(a, p)
                if is_quadratic_residue(a, p):
                    self.assertIsNotNone(r, msg=f"p={p} a={a}")
                    self.assertEqual((r * r) % p, a % p)
                else:
                    self.assertIsNone(r, msg=f"p={p} a={a}")

    def test_large_prime_squares(self):
        p = 10007
        self.assertTrue(_is_prime(p))
        for x in [1, 2, 3, 17, 100, 5000, 9999]:
            a = (x * x) % p
            r = sqrt_mod_p(a, p)
            self.assertIsNotNone(r)
            self.assertEqual((r * r) % p, a)

    def test_large_prime_nonsquare(self):
        p = 10007
        for a in range(1, 50):
            if not is_quadratic_residue(a, p):
                self.assertIsNone(sqrt_mod_p(a, p))
                break
        else:
            self.fail("no nonsquare found")

    def test_p_equiv_3_mod_4(self):
        # p=19 ≡ 3 mod 4 uses the fast path inside Tonelli
        p = 19
        for a in range(p):
            r = sqrt_mod_p(a, p)
            if r is not None:
                self.assertEqual((r * r) % p, a % p)

    def test_nth_root_n_equals_2_uses_tonelli(self):
        p = 10007
        a = (1234 * 1234) % p
        self.assertEqual((nth_root_mod_p(a, 2, p) ** 2) % p, a)


if __name__ == "__main__":
    unittest.main()
