/** Shared constants for the AKE lab. */

export const PY_FILES = [
  "ake_scanner/__init__.py",
  "ake_scanner/__main__.py",
  "ake_scanner/cli.py",
  "ake_scanner/predicates.py",
  "ake_scanner/reporting.py",
  "ake_scanner/algebra/__init__.py",
  "ake_scanner/algebra/laurent.py",
  "ake_scanner/algebra/hensel.py",
  "ake_scanner/logic/__init__.py",
  "ake_scanner/logic/primes.py",
  "ake_scanner/logic/asymptotic.py",
  "ake_scanner/logic/scanner.py",
  "examples/demo_hensel.py",
  "examples/advanced_sentences.py",
];

export const HARD_LIMIT_CAP = 1000;
export const SOFT_LIMIT_WARN = 200;
export const PYODIDE_VERSION = "0.27.5";
export const PYODIDE_CDN = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;
export const MODULUS_CANDIDATES = [3, 4, 5, 8, 12];
export const WORKER_INIT_TIMEOUT_MS = 45000;

export const TEMPLATES = {
  unit_square: {
    label: "Unit is square",
    code: `from ake_scanner.algebra.hensel import solve_x_n_equals

def predicate(F):
    """∃x  x² = 1 + t  (eventually true; exceptional p=2)."""
    return solve_x_n_equals(F.constant(1) + F.t, 2, F.precision) is not None
`,
  },
  minus_one: {
    label: "−1 is square",
    code: `from ake_scanner.algebra.hensel import is_quadratic_residue

def predicate(F):
    """∃a∈F_p  a² = −1  (mixed: p=2 or p≡1 mod 4)."""
    if F.prime == 2:
        return True
    return is_quadratic_residue(-1, F.prime)
`,
  },
  odd_val: {
    label: "Odd valuation",
    code: `from ake_scanner.algebra.hensel import solve_x_n_equals

def predicate(F):
    """∃x  x² = t  (always false: v(t)=1 is odd)."""
    return solve_x_n_equals(F.t, 2, F.precision) is not None
`,
  },
};
