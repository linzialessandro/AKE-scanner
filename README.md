# AKE Scanner

**AKE Scanner** is a computational tool designed to verify first-order sentences in the field of formal Laurent series $\mathbb{F}_p((t))$. 

This software serves as an aid for number theoretic and model theoretic research. By the Ax-Kochen-Ershov (AKE) principle, determining the truth value of a first-order sentence $\phi$ in $\mathbb{Q}_p$ for sufficiently large primes $p$ is equivalent to determining its truth value in $\mathbb{F}_p((t))$. While this tool cannot provide a formal proof for $\mathbb{Q}_p$, it allows researchers to algorithmically verify $\phi$ across a specified range of primes in $\mathbb{F}_p((t))$, providing strong empirical evidence for the asymptotic behavior of the sentence.

## Features

- **Exact Arithmetic in $\mathbb{F}_p((t))$**: Implements a `LaurentSeries` class supporting addition, multiplication, inversion, and valuation in finite characteristic $p$. Arithmetic is truncated at a user-defined precision (e.g., $O(t^{20})$).
- **Scanner Engine**: Systematically iterates through consecutive primes $p$ and instantiates the field structure for each.
- **Code-as-Input**: Users define sentences $\phi$ as Python functions, allowing for the verification of arbitrarily complex algebraic conditions (e.g., solvability of polynomial equations, existence of valuations).
- **Newton Iteration**: Includes rigorous algebraic solvers (e.g., Newton-Raphson for square roots) to constructively verify existential quantifiers.

## Installation

The project requires Python 3.8 or higher. No external dependencies are required.

```bash
git clone https://github.com/your-username/ake-scanner.git
cd ake-scanner
```

## Usage

### 1. Defining a Predicate

To check a sentence $\phi$, define a Python function that accepts a `FieldFactory` and returns a boolean. The function should constructively verify the property using the provided algebraic operations.

**Example:** Checking if $x^2 = 1+t$ has a solution (Hensel's Lemma verification).

Create a file `conjectures.py`:

```python
from src.algebra.laurent import LaurentSeries

def has_sqrt_one_plus_t(F):
    """
    Verifies if there exists x in F_p((t)) such that x^2 = 1 + t.
    Uses Newton iteration to construct the root.
    """
    # Construct the element 1 + t
    target = F.constant(1) + F.t
    
    # Check valuation (must be even for a square)
    if target.valuation % 2 != 0:
        return False

    # Attempt to solve via Newton iteration
    # ... (Implementation details omitted for brevity, see examples/)
    # Returns True if convergence is successful
    return solve_sqrt(target, precision=F.precision)
```

### 2. Running the Scanner

Use the command-line interface to run the verification against a range of primes.

```bash
python3 -m src.cli conjectures.py has_sqrt_one_plus_t --limit 100 --precision 30
```

**Arguments:**
- `file_path`: Path to the Python module containing the predicate.
- `function_name`: Name of the predicate function.
- `--limit`: Maximum prime $p$ to check.
- `--precision`: Power of $t$ at which to truncate series (default: 20).

### 3. Output Interpretation

The tool reports:
- **Verified Count**: Number of primes for which the predicate held true.
- **Failed Primes**: List of primes where the predicate was false.
- **Passed Primes**: List of primes where the predicate was true.

**Example Output:**
```
Scanning primes up to 100 with precision 30...

--- Results ---
Verified count: 24
Failed for primes: [2]
Passed for primes: [3, 5, 7, 11, ...]
```
This output empirically supports that $1+t$ is a square in $\mathbb{F}_p((t))$ for all $p > 2$.

## Project Structure

- `src/algebra/`: Generic implementation of the field $\mathbb{F}_p((t))$.
- `src/logic/`: Engine for iterating over primes and executing user predicates.
- `examples/`: Reference implementations of common predicates (e.g., Hensel's Lemma checks).
- `tests/`: Unit tests ensuring algebraic correctness (Field axioms, inverse calculation, edge cases).

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
