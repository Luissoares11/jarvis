import sympy as sp
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
)

TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application,)

x, y, z, t, n = sp.symbols("x y z t n")
SYMBOL_MAP = {"x": x, "y": y, "z": z, "t": t, "n": n}


def _parse_expr(expr_str: str):
    try:
        expr_str = expr_str.replace("^", "**")
        return parse_expr(
            expr_str,
            transformations=TRANSFORMATIONS,
            local_dict=SYMBOL_MAP,
        )
    except Exception as e:
        raise ValueError(f"Could not parse expression: '{expr_str}' — {e}")


def _format(result) -> str:
    if isinstance(result, sp.Basic):
        return str(sp.simplify(result))
    return str(result)