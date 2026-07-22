"""AKE Scanner: empirical verification of FO sentences in F_p((t))."""

__version__ = "0.3.0"

from ake_scanner.algebra.laurent import LaurentSeries
from ake_scanner.logic.scanner import FieldFactory, scan_primes
from ake_scanner.logic.verdict import Verdict, fail, ok

__all__ = [
    "LaurentSeries",
    "FieldFactory",
    "scan_primes",
    "Verdict",
    "ok",
    "fail",
    "__version__",
]
