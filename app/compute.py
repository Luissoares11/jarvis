import re
import sympy as sp
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
)
from app.memory.store import db_save_computation


TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application,)

# common symbols
x, y, z, t, n = sp.symbols("x y z t n")
SYMBOL_MAP = {"x": x, "y": y, "z": z, "t": t, "n": n}


def _parse_expr(expr_str: str):
    """Safely parse a math expression string into a sympy expression."""
    try:
        # convert ^ to ** for natural math notation
        expr_str = expr_str.replace("^", "**")
        return parse_expr(
            expr_str,
            transformations=TRANSFORMATIONS,
            local_dict=SYMBOL_MAP
        )
    except Exception as e:
        raise ValueError(f"Could not parse expression: '{expr_str}' — {e}")


def _format(result):
    """Format a sympy result into a clean string."""
    if isinstance(result, sp.Basic):
        # try to simplify before displaying
        simplified = sp.simplify(result)
        return str(simplified)
    return str(result)


# ── arithmetic ────────────────────────────────────────────────

def calculate(expr_str: str) -> str:
    try:
        expr = _parse_expr(expr_str)
        result = sp.simplify(expr)

        # if it's a pure number, evaluate it
        if result.is_number:
            evaluated = float(result)
            # show as int if it's a whole number
            if evaluated == int(evaluated):
                return str(int(evaluated))
            return f"{evaluated:.6g}"

        return _format(result)
    except Exception as e:
        return f"I couldn't calculate that: {e}"


# ── derivatives ───────────────────────────────────────────────

def differentiate(expr_str: str, var_str: str = "x", order: int = 1) -> str:
    try:
        expr = _parse_expr(expr_str)
        var = SYMBOL_MAP.get(var_str, sp.Symbol(var_str))
        result = sp.diff(expr, var, order)
        simplified = sp.simplify(result)

        order_label = {1: "", 2: " (2nd order)", 3: " (3rd order)"}.get(order, f" ({order}th order)")
        return f"d/d{var_str}{order_label} [{expr_str}] = {_format(simplified)}"
    except Exception as e:
        return f"I couldn't differentiate that: {e}"


# ── integrals ─────────────────────────────────────────────────

def integrate(expr_str: str, var_str: str = "x",
              lower=None, upper=None) -> str:
    try:
        expr = _parse_expr(expr_str)
        var = SYMBOL_MAP.get(var_str, sp.Symbol(var_str))

        if lower is not None and upper is not None:
            lower_expr = _parse_expr(str(lower))
            upper_expr = _parse_expr(str(upper))
            result = sp.integrate(expr, (var, lower_expr, upper_expr))
            result = sp.simplify(result)
            return f"∫[{lower},{upper}] {expr_str} d{var_str} = {_format(result)}"
        else:
            result = sp.integrate(expr, var)
            result = sp.simplify(result)
            return f"∫ {expr_str} d{var_str} = {_format(result)} + C"
    except Exception as e:
        return f"I couldn't integrate that: {e}"


# ── limits ────────────────────────────────────────────────────

def limit(expr_str: str, var_str: str = "x",
          point_str: str = "0", direction: str = "+") -> str:
    try:
        expr = _parse_expr(expr_str)
        var = SYMBOL_MAP.get(var_str, sp.Symbol(var_str))
        point = _parse_expr(point_str)
        result = sp.limit(expr, var, point, direction)
        result = sp.simplify(result)
        return f"lim({var_str}→{point_str}) [{expr_str}] = {_format(result)}"
    except Exception as e:
        return f"I couldn't compute that limit: {e}"


# ── equation solving ──────────────────────────────────────────

def solve_equation(expr_str: str, var_str: str = "x") -> str:
    try:
        var = SYMBOL_MAP.get(var_str, sp.Symbol(var_str))

        # handle "lhs = rhs" format
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

        sol_str = ", ".join(_format(s) for s in solutions)
        return f"{var_str} = {sol_str}"
    except Exception as e:
        return f"I couldn't solve that: {e}"


# ── unit conversions ──────────────────────────────────────────

CONVERSIONS = {
    # length
    ("km", "miles"):   lambda v: v * 0.621371,
    ("miles", "km"):   lambda v: v * 1.60934,
    ("m", "ft"):       lambda v: v * 3.28084,
    ("ft", "m"):       lambda v: v * 0.3048,
    ("m", "cm"):       lambda v: v * 100,
    ("cm", "m"):       lambda v: v / 100,
    ("m", "mm"):       lambda v: v * 1000,
    ("mm", "m"):       lambda v: v / 1000,
    ("inches", "cm"):  lambda v: v * 2.54,
    ("cm", "inches"):  lambda v: v / 2.54,

    # weight
    ("kg", "lbs"):     lambda v: v * 2.20462,
    ("lbs", "kg"):     lambda v: v / 2.20462,
    ("kg", "g"):       lambda v: v * 1000,
    ("g", "kg"):       lambda v: v / 1000,
    ("g", "mg"):       lambda v: v * 1000,
    ("mg", "g"):       lambda v: v / 1000,

    # temperature
    ("c", "f"):        lambda v: v * 9/5 + 32,
    ("f", "c"):        lambda v: (v - 32) * 5/9,
    ("c", "k"):        lambda v: v + 273.15,
    ("k", "c"):        lambda v: v - 273.15,

    # speed
    ("kmh", "mph"):    lambda v: v * 0.621371,
    ("mph", "kmh"):    lambda v: v * 1.60934,
    ("ms", "kmh"):     lambda v: v * 3.6,
    ("kmh", "ms"):     lambda v: v / 3.6,

    # energy
    ("j", "cal"):      lambda v: v / 4.184,
    ("cal", "j"):      lambda v: v * 4.184,
    ("kj", "kcal"):    lambda v: v / 4.184,
    ("kcal", "kj"):    lambda v: v * 4.184,

    # pressure
    ("pa", "atm"):     lambda v: v / 101325,
    ("atm", "pa"):     lambda v: v * 101325,
    ("bar", "pa"):     lambda v: v * 100000,
    ("pa", "bar"):     lambda v: v / 100000,
}


def convert_units(value: float, from_unit: str, to_unit: str) -> str:
    key = (from_unit.lower(), to_unit.lower())
    if key in CONVERSIONS:
        result = CONVERSIONS[key](value)
        if result == int(result):
            return f"{value} {from_unit} = {int(result)} {to_unit}"
        return f"{value} {from_unit} = {result:.4g} {to_unit}"
    return f"I don't know how to convert {from_unit} to {to_unit} yet."


# ── graphing ──────────────────────────────────────────────────

def _parse_range_value(s: str) -> float:
    """Parse a range boundary that may contain pi, e, etc."""
    s = s.strip().replace("^", "**")

    replacements = {
        "pi":  str(float(sp.pi)),
        "tau": str(float(2 * sp.pi)),
        "e":   str(float(sp.E)),
        "inf": "1e9",
    }
    for name, val in replacements.items():
        s = re.sub(rf"\b{name}\b", val, s)

    try:
        return float(_parse_expr(s).evalf())
    except Exception:
        return float(s)
    
def plot_function(expr_str: str, var_str: str = "x",
                  x_min="-10", x_max="10") -> str:
    try:
        import matplotlib.pyplot as plt
        import numpy as np

        x_min_val = _parse_range_value(str(x_min))
        x_max_val = _parse_range_value(str(x_max))

        var  = sp.Symbol(var_str)
        expr = _parse_expr(expr_str)
        f    = sp.lambdify(var, expr, modules=["numpy"])

        x_vals = np.linspace(x_min_val, x_max_val, 1000)

        y_vals = []
        for val in x_vals:
            try:
                result = float(f(val))
                y_vals.append(result if np.isfinite(result) else np.nan)
            except Exception:
                y_vals.append(np.nan)

        y_vals = np.array(y_vals, dtype=float)

        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(x_vals, y_vals, color="#378ADD", linewidth=2)
        ax.axhline(0, color="gray", linewidth=0.8, linestyle="--")
        ax.axvline(0, color="gray", linewidth=0.8, linestyle="--")
        ax.set_title(f"f({var_str}) = {expr_str}", fontsize=13)
        ax.set_xlabel(var_str)
        ax.set_ylabel(f"f({var_str})")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()

        plt.show()
        plt.close()

        return f"Here's the graph of f({var_str}) = {expr_str}."
    except Exception as e:
        return f"I couldn't plot that: {e}"
    
def plot_implicit(expr_str: str, x_range=(-2, 2), y_range=(-2, 2)) -> str:
    try:
        import matplotlib.pyplot as plt
        import numpy as np

        x_sym, y_sym = sp.symbols("x y")
        expr = _parse_expr(expr_str)
        f = sp.lambdify((x_sym, y_sym), expr, modules=["numpy"])

        x_vals = np.linspace(*x_range, 1000)
        y_vals = np.linspace(*y_range, 1000)
        X, Y = np.meshgrid(x_vals, y_vals)

        with np.errstate(invalid="ignore"):
            Z = f(X, Y)

        fig, ax = plt.subplots(figsize=(6, 6))
        ax.contour(X, Y, Z, levels=[0], colors="#378ADD", linewidths=2)
        ax.axhline(0, color="gray", linewidth=0.8, linestyle="--")
        ax.axvline(0, color="gray", linewidth=0.8, linestyle="--")
        ax.set_title(f"{expr_str} = 0", fontsize=11)
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.set_aspect("equal")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()

        plt.show()
        plt.close()

        return f"Here's the implicit plot of {expr_str} = 0."
    except Exception as e:
        return f"I couldn't plot that: {e}"    