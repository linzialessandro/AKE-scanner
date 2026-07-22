# AKE Scanner

**AKE Scanner** verifies first-order sentences in the field of formal Laurent series \(\mathbb{F}_p((t))\), as an empirical aid for number theory and model theory.

By the **Ax–Kochen–Ershov (AKE) principle**, the truth of a first-order sentence \(\phi\) in \(\mathbb{Q}_p\) for all sufficiently large primes \(p\) is equivalent to its truth in \(\mathbb{F}_p((t))\). This tool cannot *prove* statements about \(\mathbb{Q}_p\), but it can algorithmically check \(\phi\) across a range of primes in \(\mathbb{F}_p((t))\), giving strong evidence for asymptotic behaviour and listing exceptional primes.

## Features

- **Exact truncated arithmetic** in \(\mathbb{F}_p((t))\): addition, multiplication, inversion, division, integer powers, valuation, unit part, residue.
- **Hensel / Newton solvers**: square roots, \(n\)-th roots, and univariate Hensel lifting so existential quantifiers can be checked *constructively*.
- **Prime scanner**: iterate primes (or a custom list), separate **failures** from **runtime errors**, and report asymptotic thresholds.
- **Code-as-input**: encode \(\phi\) as a Python predicate `FieldFactory -> bool` or structured `Verdict` (witness / obstruction code).
- **Explain mode**: per-prime reasons (`odd_valuation`, `p_divides_n`, residue witnesses, Laurent series witnesses) via CLI `--explain` and clickable primes in the web lab.
- **CLI** with text, JSON, and CSV reports (`ake-scan`).
- **Web lab** (GitHub Pages): same engine in the browser (Pyodide), with guided demos, prime strip, residue analysis, custom predicates, share links, and export.

## Web lab

Live site (same package as the CLI, no install required):

**https://linzialessandro.github.io/AKE-scanner/**

### What you can do

1. **Guided stories** — one-click demos of the three main shapes: `eventually_true`, `always_false`, and `mixed`.
2. **Prime strip** — pass / fail / error per prime; live progress while scanning.
3. **Pattern story** — plain-language AKE readout (threshold \(N\), exceptional primes, clean tail) plus optional CLI text / JSON.
4. **Residue analysis** — for `mixed` patterns, suggest \(p \bmod m\) and show a per-class histogram; optional residue lens on the strip.
5. **Custom playground** — write `predicate(F) -> bool` in-browser (templates included); code stays in your tab.
6. **Share & export** — copy a URL with settings (`?p=…&l=80&mod=4&autorun=1`), or download report `.txt` / JSON / CSV; copy the equivalent `ake-scan` command.
7. **Power use** — scans prefer a Web Worker (UI stays responsive); prime limit up to 1000; main-thread fallback if the worker cannot start.
8. **Explain a prime** — click a strip cell for obstruction codes or a constructive witness (when the predicate returns a `Verdict`).

### How to read the lab (short)

| Pattern | What to look for on the strip |
|---------|--------------------------------|
| `eventually_true` | Finite mess, then a long green tail |
| `eventually_false` | Finite early passes, then a red tail |
| `always_*` | Uniform colour for the whole range |
| `mixed` | Alternation; use residue analysis, not a single \(N\) |

Pass/fail is a constructive check in \(\mathbb{F}_p((t))\) at finite precision — not a proof about \(\mathbb{Q}_p\). Errors (amber) are runtime exceptions, kept separate from mathematical failure.

### Preview locally

The site is static under `docs/`. The package is vendored into `docs/py/` for Pyodide:

```bash
./scripts/sync_web_py.sh
python3 -m http.server -d docs 8000
# open http://127.0.0.1:8000/
```

Frontend sources live in `docs/assets/` (entry `app.js`, modules under `docs/assets/js/`). GitHub Actions (`.github/workflows/pages.yml`) re-syncs `docs/py` and deploys Pages on every push to `main`. Enable **Settings → Pages → Source: GitHub Actions** once if needed.

## Installation

Requires Python 3.9+.

```bash
git clone https://github.com/linzialessandro/AKE-scanner.git
cd AKE-scanner
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

Demo predicates in this repo (see the full table below):

```bash
ake-scan examples/demo_hensel.py predicate_one_plus_t_is_square -l 50 -q
ake-scan examples/demo_hensel.py predicate_one_plus_t_is_cube -l 30 -q
ake-scan examples/demo_hensel.py predicate_t_is_square -l 20 -q
# Non-trivial / mixed patterns:
ake-scan examples/demo_hensel.py predicate_minus_one_is_square -l 80 -v
ake-scan examples/demo_hensel.py predicate_primitive_cube_root_of_unity -l 60 -v
ake-scan examples/demo_hensel.py predicate_x_cubed_minus_x_equals_t -l 40 -q
ake-scan examples/demo_hensel.py predicate_artin_schreier_valuation_obstruction -l 30 -q
# Simultaneous systems / quantifiers / (v, ac) language:
ake-scan examples/advanced_sentences.py predicate_sum_of_two_squares_equals_t -l 60 -v
ake-scan examples/advanced_sentences.py predicate_forall_a_exists_sqrt_one_plus_a_t -l 40 -q
ake-scan examples/advanced_sentences.py predicate_exists_even_valuation_nonsquare_ac -l 40 -q
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
| `--explain` | Per-prime obstruction / witness section (and force capture for bare bools) |

Demo predicates in `examples/demo_hensel.py` return structured `Verdict` objects automatically (explanations appear even without `--explain`; use `-v` or `--explain` to print them in the text report).

```bash
ake-scan examples/demo_hensel.py predicate_t_is_square -l 20 --explain
ake-scan examples/demo_hensel.py predicate_one_plus_t_is_square -l 30 -v
```

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
  algebra/             # LaurentSeries + Hensel/Newton solvers
  logic/
    primes.py          # prime generation
    asymptotic.py      # AKE pattern classification
    verdict.py         # Verdict, ok/fail, witness serialization
    diagnose.py        # constructive obstruction/witness helpers
    scanner.py         # FieldFactory, scan_primes
  predicates.py        # load/resolve user predicate modules
  reporting.py         # text + CSV reports
  cli.py               # ake-scan entry (argparse + main)
examples/              # Reference predicates (demo_hensel, advanced_sentences)
docs/                  # GitHub Pages root
  index.html           # lab UI copy + structure
  assets/app.js        # boot module
  assets/js/           # share, runtime, modulus, results, …
  assets/catalog.js    # sentence catalog for the lab
  py/                  # vendored package (scripts/sync_web_py.sh)
tests/                 # Algebra, Hensel, scanner, sentence checks
```

## Examples included

| Predicate | Expected pattern | Notes |
|-----------|------------------|-------|
| `predicate_one_plus_t_is_square` | `eventually_true` | Exceptional \(p=2\) |
| `predicate_one_plus_t_is_cube` | `eventually_true` | Exceptional \(p=3\) (\(p \mid n\)) |
| `predicate_one_plus_t_is_fifth_power` | `eventually_true` | Exceptional \(p=5\) |
| `predicate_one_plus_two_t_is_fourth_power` | `eventually_true` | Exceptional \(p=2\) |
| `predicate_one_plus_t_plus_t_squared_is_square` | `eventually_true` | Richer unit \(1+t+t^2\) |
| `predicate_one_over_one_plus_t_is_square` | `eventually_true` | \(x^2(1+t)=1\) |
| `predicate_quadratic_with_parameter` | `eventually_true` | \(x^2=1+t+2t^3\) |
| `predicate_t_is_square` | `always_false` | Odd valuation \(v(t)=1\) |
| `predicate_odd_valuation_never_a_square` | `always_false` | \(x^2=t^3\) |
| `predicate_artin_schreier_valuation_obstruction` | `always_false` | \(x^p-x=t^{-1}\) impossible |
| `predicate_t_squared_is_square` | `always_true` | Witness \(x=t\) |
| `predicate_one_plus_t_inv_squared_is_square` | `always_true` | \(x^2=1+t^{-2}\) |
| `predicate_x_cubed_minus_x_equals_t` | `always_true` | Hensel lift of \(X^3-X-t\) |
| `predicate_minus_one_is_square` | `mixed` | \(p=2\) or \(p\equiv1\pmod4\) |
| `predicate_two_is_square` | `mixed` | \(p=2\) or \(p\equiv\pm1\pmod8\) |
| `predicate_minus_one_and_two_are_squares` | `mixed` | Intersection (\(\approx p\equiv1\pmod8\)) |
| `predicate_x_squared_plus_one` | `mixed` | Hensel form of \(-1\) square |
| `predicate_primitive_cube_root_of_unity` | `mixed` | \(x^2+x+1=0\); \(p\equiv1\pmod3\) |

### Advanced examples (`examples/advanced_sentences.py`)

| Family | Predicate | Expected pattern | FO flavour |
|--------|-----------|------------------|------------|
| Systems | `predicate_sum_of_two_squares_equals_t` | `mixed` | ∃x∃y x²+y²=t (cancellation) |
| Systems | `predicate_sum_of_two_squares_equals_one_plus_t` | `eventually_true` | ∃x∃y x²+y²=1+t |
| Systems | `predicate_independent_simultaneous_squares` | `eventually_true` | ∃x∃y (x²=1+t ∧ y²=1+2t) |
| Systems | `predicate_simultaneous_i_and_sqrt_one_plus_t` | `mixed` | ∃x∃y (x²=-1 ∧ y²=1+t) |
| Systems | `predicate_simultaneous_product_and_sum` | mixed / residue | xy=1 ∧ x+y=3 |
| Systems | `predicate_pythagorean_unit_circle` | `always_true` | x²+y²=1 |
| Quantifiers | `predicate_forall_a_exists_sqrt_one_plus_a_t` | `eventually_true` | ∀a∈F_p ∃x x²=1+a t |
| Quantifiers | `predicate_forall_nonzero_square_a_exists_sqrt_a_plus_t` | `eventually_true` | ∀ square a≠0 ∃x x²=a+t |
| Quantifiers | `predicate_exists_nonsquare_forall_not_square` | `eventually_true` | ∃c ∀a a²≠c |
| Quantifiers | `predicate_forall_a_exists_artin_schreier_preimage` | `always_false` | ∀a ∃b b²−b=a |
| Quantifiers | `predicate_forall_a_quadratic_T2_aT_1_splits` | `eventually_false` | ∀a ∃r r²+a r+1=0 |
| Quantifiers | `predicate_exists_uniform_square_root_base` | `eventually_true` | ∃u ∀a ∃x x²=u+a t |
| Quantifiers | `predicate_forall_val_in_window_even_of_squares` | `always_true` | odd val ⇒ not square |
| Value / ac | `predicate_exists_uniformizer_ac_one` | `always_true` | ∃π (v=1 ∧ ac=1) |
| Value / ac | `predicate_exists_val_one_with_nonsquare_ac` | `eventually_true` | ∃x (v=1 ∧ ac nonsquare) |
| Value / ac | `predicate_exists_even_valuation_nonsquare_ac` | `eventually_true` | even v, nonsquare ac ⇏ square |
| Value / ac | `predicate_value_group_is_2_divisible` | `always_false` | Γ ≅ ℤ not 2-divisible |
| Value / ac | `predicate_ultrametric_cancellation` | `always_true` | strict triangle ineq. |
| Value / ac | `predicate_ac_multiplicative_on_samples` | `always_true` | ac(xy)=ac(x)ac(y) |
| Value / ac | `predicate_valuation_of_frobenius_gap` | `always_true` | v(x^p−x)=p v(x) for v(x)<0 |
| Value / ac | `predicate_compatible_v_ac_square_criterion_on_units` | `always_true` | constant square iff residue square |

Omit the function name to list every predicate in a file:

```bash
ake-scan examples/demo_hensel.py
ake-scan examples/advanced_sentences.py
PYTHONPATH=src python -m ake_scanner examples/demo_hensel.py predicate_one_plus_t_is_cube -l 30
```

## License

MIT. See [LICENSE](LICENSE).
