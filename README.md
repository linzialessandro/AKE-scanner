# AKE Scanner

**AKE Scanner** verifies first-order sentences in the field of formal Laurent series \(\mathbb{F}_p((t))\), as an empirical aid for number theory and model theory.

By the **Ax–Kochen–Ershov (AKE) principle**, the truth of a first-order sentence \(\phi\) in \(\mathbb{Q}_p\) for all sufficiently large primes \(p\) is equivalent to its truth in \(\mathbb{F}_p((t))\). This tool cannot *prove* statements about \(\mathbb{Q}_p\), but it can algorithmically check \(\phi\) across a range of primes in \(\mathbb{F}_p((t))\), giving strong evidence for asymptotic behaviour and listing exceptional primes.

## Features

- **Exact truncated arithmetic** in \(\mathbb{F}_p((t))\): addition, multiplication, inversion, division, integer powers, valuation, unit part, residue.
- **Hensel / Newton solvers**: square roots, \(n\)-th roots, and univariate Hensel lifting so existential quantifiers can be checked *constructively*.
- **Prime scanner**: iterate primes (or a custom list), separate **failures** from **runtime errors**, and report asymptotic thresholds.
- **Code-as-input**: encode \(\phi\) as a Python predicate `FieldFactory -> bool`.
- **CLI** with text, JSON, and CSV reports (`ake-scan`).

## Installation

Requires Python 3.9+.

```bash
git clone https://github.com/your-username/ake-scanner.git
cd ake-scanner
python3 -m venv .venv
source .venv/bin/activate
pip install .          # regular install (recommended)
```

**Do not use `pip install -e .` on macOS iCloud paths.** Editable installs drop a `.pth` file that macOS often marks as hidden; Python 3.11+ then *skips* that file, so you get `ModuleNotFoundError: No module named 'ake_scanner'`. A normal `pip install .` copies the package into `site-packages` and works.

### Run without installing

From the repo root (uses the local `src/` tree):

```bash
./ake-scan examples/demo_hensel.py predicate_one_plus_t_is_square -l 50
# or:
PYTHONPATH=src python3 -m ake_scanner examples/demo_hensel.py predicate_one_plus_t_is_square -l 50
```

### Tests

```bash
python -m unittest discover -s tests -v
```

## Quick start

### 1. Define a predicate

```python
# conjectures.py
from ake_scanner import FieldFactory
from ake_scanner.algebra.hensel import solve_x_n_equals

def has_sqrt_one_plus_t(F: FieldFactory) -> bool:
    """Exists x in F_p((t)) with x^2 = 1 + t."""
    target = F.constant(1) + F.t
    return solve_x_n_equals(target, 2, F.precision) is not None
```

### 2. Run the scanner

Both the **file** and the **predicate name** are required:

```bash
ake-scan conjectures.py has_sqrt_one_plus_t --limit 100 --precision 30
```

Demo predicates in this repo:

```bash
ake-scan examples/demo_hensel.py predicate_one_plus_t_is_square -l 50 -q
ake-scan examples/demo_hensel.py predicate_one_plus_t_is_cube -l 30 -q
ake-scan examples/demo_hensel.py predicate_t_is_square -l 20 -q
```

**Useful flags**

| Flag | Meaning |
|------|---------|
| `-l` / `--limit` | Upper bound on primes (default 50) |
| `-s` / `--start` | Lower bound on primes (default 2) |
| `--primes 3,5,7` | Explicit prime list |
| `-p` / `--precision` | Truncation degree for series (default 20) |
| `--json` / `--csv` | Machine-readable output |
| `-q` / `--quiet` | Suppress loading banner (summary only) |
| `-v` / `--verbose` | Add failed/passed prime lists after the summary |
| `--full` | Full detail including tail primes |
| `--progress` | Print scan progress |

### 3. Interpret the output (asymptotic-first)

Reports lead with the AKE-relevant pattern, not a raw pass list:

```
--- AKE asymptotic summary ---
Pattern:       eventually_true
Claim:         holds for all scanned p > 2
Threshold N:   2
Exceptional:   [2]
Clean tail:    14 primes (up to p=47), all passed
Readout:       AKE-style evidence that φ holds for large p ...
```

| Pattern | Meaning |
|---------|---------|
| `eventually_true` | After a finite exceptional set, all larger *scanned* primes pass |
| `eventually_false` | After a finite set, all larger scanned primes fail |
| `always_true` / `always_false` | Constant on the whole range |
| `mixed` | No stable threshold (e.g. depends on \(p \bmod m\)) |

A clean tail must be large enough (~25% of the sample, ≥ 2 primes) so one lucky last prime does not fake “eventually true.” Raise `-l` to stress-test \(N\). Use `--json` for the full `asymptotic` object.

**Caveats**

- Truncation is **absolute** (\(O(t^{P+1})\)); see the docstring on `LaurentSeries` for inverse product guarantees when valuation is negative.
- A predicate returning `False` may mean “no witness” or “solver could not lift at this precision.” Runtime exceptions are reported separately as **errors**, not mathematical failures.
- AKE is asymptotic: the tool is built to highlight the large-\(p\) pattern and exceptional primes.

## Library API (brief)

```python
from ake_scanner import LaurentSeries, FieldFactory, scan_primes
from ake_scanner.algebra.hensel import sqrt_series, nth_root, hensel_lift

# Arithmetic
a = LaurentSeries({0: 1, 1: 1}, prime=5, precision=20)
x = sqrt_series(a)          # Newton square root or None
cube = nth_root(a, 3)       # cube root or None

# Scan
def pred(F: FieldFactory) -> bool:
    return sqrt_series(F.constant(1) + F.t, F.precision) is not None

report = scan_primes(pred, prime_limit=50, precision=20)
print(report["failed_primes"], report["holds_for_p_greater_than"])
```

## Project layout

```
src/ake_scanner/
  algebra/          # LaurentSeries + Hensel/Newton solvers
  logic/            # FieldFactory, prime generation, scan_primes
  cli.py            # ake-scan entry point
examples/           # Reference predicates (Hensel demos)
tests/              # Algebra, Hensel, scanner, sentence checks
```

## Examples included

| Predicate | Expected behaviour |
|-----------|-------------------|
| `predicate_one_plus_t_is_square` | Fails only at \(p=2\) |
| `predicate_t_is_square` | Fails all primes (odd valuation) |
| `predicate_one_plus_t_is_cube` | Fails at \(p=3\) (derivative / \(p \mid n\)) |

```bash
PYTHONPATH=src python -m ake_scanner examples/demo_hensel.py predicate_one_plus_t_is_cube -l 30
```

## License

MIT. See [LICENSE](LICENSE).
