import argparse
import sys
import os
import importlib.util
from typing import Callable
from src.logic.scanner import scan_primes, FieldFactory

def load_predicate_from_file(file_path: str, function_name: str) -> Callable[[FieldFactory], bool]:
    """
    Dynamically loads a predicate function from a given Python file.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    module_name = os.path.splitext(os.path.basename(file_path))[0]
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {file_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        raise ImportError(f"Error executing module {file_path}: {e}")
    if not hasattr(module, function_name):
        raise AttributeError(f"Function '{function_name}' not found in {file_path}")

    func = getattr(module, function_name)
    if not callable(func):
        raise TypeError(f"'{function_name}' is not callable")

    return func

def main():
    parser = argparse.ArgumentParser(
        description="AKE-scanner CLI: Verify first-order sentences in F_p((t))."
    )
    
    parser.add_argument(
        "file_path", 
        help="Path to the Python file containing the predicate function."
    )
    parser.add_argument(
        "function_name", 
        help="Name of the predicate function (must accept FieldFactory and return bool)."
    )
    parser.add_argument(
        "-l", "--limit", 
        type=int, 
        default=50, 
        help="Upper limit for primes to scan (default: 50)."
    )
    parser.add_argument(
        "-p", "--precision", 
        type=int, 
        default=20, 
        help="Precision for Laurent series arithmetic (default: 20)."
    )

    args = parser.parse_args()

    try:
        print(f"Loading '{args.function_name}' from '{args.file_path}'...")
        predicate = load_predicate_from_file(args.file_path, args.function_name)
        
        print(f"Scanning primes up to {args.limit} with precision {args.precision}...")
        results = scan_primes(predicate, args.limit, args.precision)
        
        print("\n--- Results ---")
        print(f"Verified count: {results['verified_count']}")
        
        if results['failed_primes']:
            print(f"Failed for primes: {results['failed_primes']}")
        else:
            print("No failures found.")
            
        if results['details']:
            print("\nErrors encountered:")
            for p, error in results['details'].items():
                print(f"  p={p}: {error}")
                
        if results['passed_primes']:
            print(f"\nPassed for primes: {results['passed_primes']}")
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
