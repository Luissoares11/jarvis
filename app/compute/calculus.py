import sympy as sp
from app.compute._base import _parse_expr, _format, SYMBOL_MAP


def differentiate(expr_str: str, var_str: str = "x", order: int = 1) -> str:
    try:
        expr = _parse_expr(expr_str)
        var = SYMBOL_MAP.get(var_str, sp.Symbol(var_str))
        result = sp.simplify(sp.diff(expr, var, order))
        order_label = {1: "", 2: " (2nd order)", 3: " (3rd order)"}.get(order, f" ({order}th order)")
        return f"d/d{var_str}{order_label} [{expr_str}] = {_format(result)}"
    except Exception as e:
        return f"I couldn't differentiate that: {e}"


def integrate(expr_str: str, var_str: str = "x", lower=None, upper=None) -> str:
    try:
        expr = _parse_expr(expr_str)
        var = SYMBOL_MAP.get(var_str, sp.Symbol(var_str))

        if lower is not None and upper is not None:
            lower_expr = _parse_expr(str(lower))
            upper_expr = _parse_expr(str(upper))
            result = sp.simplify(sp.integrate(expr, (var, lower_expr, upper_expr)))
            return f"∫[{lower},{upper}] {expr_str} d{var_str} = {_format(result)}"
        else:
            result = sp.simplify(sp.integrate(expr, var))
            return f"∫ {expr_str} d{var_str} = {_format(result)} + C"
    except Exception as e:
        return f"I couldn't integrate that: {e}"


def limit(expr_str: str, var_str: str = "x", point_str: str = "0", direction: str = "+") -> str:
    try:
        expr = _parse_expr(expr_str)
        var = SYMBOL_MAP.get(var_str, sp.Symbol(var_str))
        point = _parse_expr(point_str)
        result = sp.simplify(sp.limit(expr, var, point, direction))
        return f"lim({var_str}→{point_str}) [{expr_str}] = {_format(result)}"
    except Exception as e:
        return f"I couldn't compute that limit: {e}"