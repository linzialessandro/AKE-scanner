"""Load and resolve user predicate callables from Python files."""

from __future__ import annotations

import inspect
import importlib.util
import os
import sys
from types import ModuleType
from typing import Callable, List, Optional, Tuple

from ake_scanner.logic.scanner import FieldFactory


def load_module(file_path: str) -> ModuleType:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    module_name = os.path.splitext(os.path.basename(file_path))[0]
    # Unique name so reloads from different paths do not clash
    unique_name = f"ake_user_predicate_{module_name}_{abs(hash(os.path.abspath(file_path)))}"
    spec = importlib.util.spec_from_file_location(unique_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {file_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        raise ImportError(f"Error executing module {file_path}: {e}") from e
    return module


def looks_like_predicate(name: str, func: Callable) -> bool:
    """
    Heuristic for scan predicates: public callable with one required
    positional parameter that is a field factory (name F / factory / …),
    or a function whose name starts with ``predicate_``.
    """
    try:
        sig = inspect.signature(func)
    except (TypeError, ValueError):
        return False
    required = [
        p
        for p in sig.parameters.values()
        if p.default is inspect.Parameter.empty
        and p.kind
        in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        )
    ]
    if len(required) != 1:
        return False
    if name.startswith("predicate_"):
        return True
    first = required[0].name.lower()
    return first in ("f", "factory", "field", "field_factory", "ff")


def list_predicates(module: ModuleType) -> List[Tuple[str, Callable]]:
    """
    Public callables defined in the module that look like predicates
    (one required argument, e.g. FieldFactory -> bool).
    """
    found: List[Tuple[str, Callable]] = []
    for name, obj in sorted(vars(module).items()):
        if name.startswith("_"):
            continue
        if not callable(obj):
            continue
        # Prefer functions defined in this module (skip re-exports of helpers)
        if inspect.isfunction(obj) and getattr(obj, "__module__", None) != module.__name__:
            continue
        if not looks_like_predicate(name, obj):
            continue
        found.append((name, obj))
    return found


def load_predicate_from_file(
    file_path: str, function_name: str
) -> Callable[[FieldFactory], bool]:
    """Dynamically load a predicate function from a Python file."""
    module = load_module(file_path)
    if not hasattr(module, function_name):
        available = [n for n, _ in list_predicates(module)]
        hint = f" Available predicates: {', '.join(available)}" if available else ""
        raise AttributeError(
            f"Function '{function_name}' not found in {file_path}.{hint}"
        )

    func = getattr(module, function_name)
    if not callable(func):
        raise TypeError(f"'{function_name}' is not callable")

    return func


def resolve_predicate(
    file_path: str, function_name: Optional[str]
) -> Tuple[str, Callable[[FieldFactory], bool]]:
    """
    Resolve which predicate to run.

    - If ``function_name`` is given, load it.
    - If omitted and exactly one predicate is found, use it.
    - If omitted and several are found, raise with a list to choose from.
    """
    if function_name:
        return function_name, load_predicate_from_file(file_path, function_name)

    module = load_module(file_path)
    preds = list_predicates(module)
    if not preds:
        raise AttributeError(
            f"No predicate functions found in {file_path}. "
            "Define a function that takes one argument (FieldFactory) and returns bool."
        )
    if len(preds) == 1:
        name, func = preds[0]
        return name, func

    names = ", ".join(n for n, _ in preds)
    raise SystemExit(
        f"Multiple predicates in {file_path}. Specify one:\n"
        + "\n".join(f"  ake-scan {file_path} {n}" for n, _ in preds)
        + f"\n\nAvailable: {names}"
    )
