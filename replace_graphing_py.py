import sys

with open("latex_calculator.py", "r") as f:
    content = f.read()

# Inject plot detection before Steps
old_steps = """    # ── Steps ─────────────────────────────────────────────────────────────────
    stepsMode = settings.get('stepsMode', 'off')"""

new_plot = """    # ── Plot Detection ────────────────────────────────────────────────────────
    plot_data = None
    try:
        def _to_plot_string(ex) -> str:
            return str(ex).replace('**', '^')

        from sympy import Integral
        if expr.has(Integral):
            integrals = expr.atoms(Integral)
            if len(integrals) == 1:
                i_node = list(integrals)[0]
                if len(i_node.limits) == 1 and len(i_node.limits[0]) == 3:
                    var, a, b = i_node.limits[0]
                    if a.is_real and b.is_real and len(i_node.function.free_symbols) <= 1:
                        plot_data = {
                            "fn": _to_plot_string(i_node.function),
                            "bounds": [float(a), float(b)]
                        }
        if not plot_data:
            fs = result.free_symbols
            if len(fs) == 1:
                plot_data = {
                    "fn": _to_plot_string(result)
                }
    except Exception:
        pass

    # ── Steps ─────────────────────────────────────────────────────────────────
    stepsMode = settings.get('stepsMode', 'off')"""

content = content.replace(old_steps, new_plot)

# Add plot to payload
old_payload = """    payload: dict = {"status": "success", "result": result_latex}
    if approx_latex is not None:
        payload["approx"] = approx_latex
    if steps_list:
        payload["steps"] = steps_list
    return json.dumps(payload)"""

new_payload = """    payload: dict = {"status": "success", "result": result_latex}
    if approx_latex is not None:
        payload["approx"] = approx_latex
    if steps_list:
        payload["steps"] = steps_list
    if plot_data:
        payload["plot"] = plot_data
    return json.dumps(payload)"""

content = content.replace(old_payload, new_payload)

with open("latex_calculator.py", "w") as f:
    f.write(content)

print("Patched python backend for graphing successfully.")
