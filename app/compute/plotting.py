import os
import re
import sympy as sp
from app.compute._base import _parse_expr


def _parse_range_value(s: str) -> float:
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


def plot_function(expr_str: str, var_str: str = "x", x_min="-10", x_max="10") -> str:
    try:
        import plotly.graph_objects as go
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
                y_vals.append(result if np.isfinite(result) else None)
            except Exception:
                y_vals.append(None)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=x_vals.tolist(),
            y=y_vals,
            mode='lines',
            line=dict(color='#378ADD', width=2),
            name=f'f({var_str}) = {expr_str}'
        ))
        fig.update_layout(
            title=f'f({var_str}) = {expr_str}',
            paper_bgcolor='#050a0f',
            plot_bgcolor='#071828',
            font=dict(color='#70b8f0', family='Courier New'),
            xaxis=dict(gridcolor='#0d2a40', zerolinecolor='#1a3a55'),
            yaxis=dict(gridcolor='#0d2a40', zerolinecolor='#1a3a55'),
        )

        html = fig.to_html(full_html=True, include_plotlyjs=True)

        os.makedirs("data/plots", exist_ok=True)
        filename = f"plot_{abs(hash(expr_str))}.html"
        path = f"data/plots/{filename}"
        with open(path, "w") as f:
            f.write(html)

        return f"PLOT:{filename}"
    except Exception as e:
        return f"I couldn't plot that: {e}"


def plot_implicit(expr_str: str, x_range=(-2, 2), y_range=(-2, 2)) -> str:
    try:
        import plotly.graph_objects as go
        import numpy as np

        if "=" in expr_str:
            parts = expr_str.split("=", 1)
            expr_str_parsed = f"({parts[0].strip()}) - ({parts[1].strip()})"
        else:
            expr_str_parsed = expr_str

        x_sym, y_sym = sp.symbols("x y")
        expr = _parse_expr(expr_str_parsed)
        f = sp.lambdify((x_sym, y_sym), expr, modules=["numpy"])

        x_vals = np.linspace(*x_range, 500)
        y_vals = np.linspace(*y_range, 500)
        X, Y = np.meshgrid(x_vals, y_vals)

        with np.errstate(invalid="ignore"):
            Z = f(X, Y)

        fig = go.Figure()
        fig.add_trace(go.Contour(
            x=x_vals.tolist(),
            y=y_vals.tolist(),
            z=Z.tolist(),
            contours=dict(start=0, end=0, size=1, coloring='lines'),
            line=dict(color='#378ADD', width=2),
            showscale=False,
            name=f'{expr_str} = 0'
        ))
        fig.update_layout(
            title=f'{expr_str}',
            paper_bgcolor='#050a0f',
            plot_bgcolor='#071828',
            font=dict(color='#70b8f0', family='Courier New'),
            xaxis=dict(gridcolor='#0d2a40', zerolinecolor='#1a3a55'),
            yaxis=dict(gridcolor='#0d2a40', zerolinecolor='#1a3a55'),
        )

        html = fig.to_html(full_html=True, include_plotlyjs=True)

        os.makedirs("data/plots", exist_ok=True)
        filename = f"plot_implicit_{abs(hash(expr))}.html"
        path = f"data/plots/{filename}"
        with open(path, "w") as f:
            f.write(html)

        return f"PLOT:{filename}"
    except Exception as e:
        return f"I couldn't plot that: {e}"