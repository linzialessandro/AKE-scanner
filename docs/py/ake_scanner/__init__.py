"""AKE Scanner: empirical verification of FO sentences in F_p((t))."""

__version__ = "0.2.0"

from ake_scanner.algebra.laurent import LaurentSeries
from ake_scanner.logic.scanner import FieldFactory, scan_primes

__all__ = [
    "LaurentSeries",
    "FieldFactory",
    "scan_primes",
    "__version__",
]
