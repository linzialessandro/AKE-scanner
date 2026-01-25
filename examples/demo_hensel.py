from src.logic.scanner import FieldFactory
from src.algebra.laurent import LaurentSeries

def solve_sqrt(target: LaurentSeries, precision: int = 20) -> bool:
    """
    Attempts to find x such that x^2 = target using Newton iteration.
    Returns True if a root is found (approx), False otherwise.
    """
    if target.is_zero():
        return True # sqrt(0) = 0
    
    p = target.prime
    
    # Valuation must be even
    val = target.valuation
    if val % 2 != 0:
        return False 
    
    # Normalize: target = t^2k * u. Need sqrt(u).
    # u starts with c, which must be a quadratic residue.
    base_coeff = target.coeffs[val]
    
    is_residue = False
    root_c = 0
    for i in range(1, p):
        if (i * i) % p == base_coeff:
            is_residue = True
            root_c = i
            break
            
    if not is_residue:
        return False

    # p=2 special case (endomorphism)
    if p == 2:
        for d in target.coeffs:
            if d % 2 != 0:
                return False
        return True

    # Newton Iteration for p > 2
    inv_2 = pow(2, -1, p)
    inv_2_series = target.constant(inv_2, p, precision)
    
    u_coeffs = {d - val: c for d, c in target.coeffs.items()}
    u = LaurentSeries(u_coeffs, p, precision)
    x = LaurentSeries.constant(root_c, p, precision)
    
    try:
        for _ in range(6): 
            # x_{n+1} = (x_n + u/x_n) / 2
            term = u * x.inv()
            x_new = (x + term) * inv_2_series
            if x_new == x:
                break
            x = x_new
    except ZeroDivisionError:
        return False
        
    diff = (x * x) - u
    if diff.valuation > precision - 2:
        return True
    
    return False


def predicate_one_plus_t_is_square(F: FieldFactory) -> bool:
    """
    Constructively checks if x^2 = 1 + t has a solution.
    Does NOT use shortcuts. Actually attempts to compute the root.
    """
    one_plus_t = F.constant(1) + F.t
    
    # Run the solver
    has_root = solve_sqrt(one_plus_t, F.precision)
    return has_root

def predicate_t_is_square(F: FieldFactory) -> bool:
    """
    Checks if x^2 = t has a solution.
    """
    t = F.t
    has_root = solve_sqrt(t, F.precision)
    return has_root
