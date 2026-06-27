import sympy as sp
from app.compute._base import _parse_expr, _format, SYMBOL_MAP


def calculate(expr_str: str) -> str:
    try:
        expr = _parse_expr(expr_str)
        result = sp.simplify(expr)

        if result.is_number:
            evaluated = float(result)
            if evaluated == int(evaluated):
                return str(int(evaluated))
            return f"{evaluated:.6g}"

        return _format(result)
    except Exception as e:
        return f"I couldn't calculate that: {e}"


def solve_equation(expr_str: str, var_str: str = "x") -> str:
    try:
        var = SYMBOL_MAP.get(var_str, sp.Symbol(var_str))

        if "=" in expr_str:
            parts = expr_str.split("=", 1)
            lhs = _parse_expr(parts[0].strip())
            rhs = _parse_expr(parts[1].strip())
            expr = lhs - rhs
        else:
            expr = _parse_expr(expr_str)

        solutions = sp.solve(expr, var)

        if not solutions:
            return f"No solutions found for {expr_str} = 0"

        if len(solutions) == 1:
            return f"{var_str} = {_format(solutions[0])}"

        return f"{var_str} = {', '.join(_format(s) for s in solutions)}"
    except Exception as e:
        return f"I couldn't solve that: {e}"