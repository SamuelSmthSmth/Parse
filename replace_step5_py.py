import sys

with open("latex_calculator.py", "r") as f:
    content = f.read()

# Add _generate_steps at the top level
steps_func = """
def _generate_steps(expr, mode: str) -> list[str]:
    from sympy import simplify, Integral, Derivative, apart
    steps = []
    
    if mode == 'raw':
        steps.append(to_latex(expr))
        try:
            expanded = expr.expand()
            if expanded != expr:
                steps.append(to_latex(expanded))
        except Exception:
            pass
        try:
            simplified = simplify(expr)
            # Make sure we don't duplicate
            if len(steps) == 0 or to_latex(simplified) != steps[-1]:
                if simplified != expr:
                    steps.append(to_latex(simplified))
        except Exception:
            pass

    elif mode == 'friendly':
        try:
            ap = apart(expr)
            if ap != expr:
                steps.append(to_latex(ap))
        except Exception:
            pass
            
        if expr.has(Integral):
            for i in expr.atoms(Integral):
                try:
                    from sympy.integrals.manualintegrate import manualintegrate
                    limits = i.limits
                    if len(limits) == 1 and len(limits[0]) == 1:
                        var = limits[0][0]
                        mi = manualintegrate(i.function, var)
                        if mi != i:
                            steps.append(to_latex(mi))
                except Exception:
                    pass
                    
        if expr.has(Derivative):
            for d in expr.atoms(Derivative):
                try:
                    evaluated = d.doit()
                    if evaluated != d:
                        steps.append(to_latex(evaluated))
                except Exception:
                    pass
    
    return steps
"""

# inject right before evaluate_latex
inject_target = "def evaluate_latex(latex_input: str, settings_json: str = '{}') -> str:"
content = content.replace(inject_target, steps_func + "\n" + inject_target)

# Add logic to evaluate_latex
eval_old = """    # ── Evaluate ──────────────────────────────────────────────────────────────
    try:
        evaluated = expr.doit()
        result    = simplify(evaluated)

    except NotImplementedError as exc:
        return _error(f"Cannot evaluate (no closed form): {_short(exc)}")
    except (TypeError, AttributeError, ValueError) as exc:
        return _error(f"Evaluation error: {_short(exc)}")
    except Exception as exc:
        return _error(f"Unexpected error: {_short(exc)}")

    # ── Serialise ─────────────────────────────────────────────────────────────
    try:
        result_latex = to_latex(result)
    except Exception as exc:
        return _error(f"Serialisation error: {_short(exc)}")"""

eval_new = """    # ── Evaluate ──────────────────────────────────────────────────────────────
    try:
        evaluated = expr.doit()
        result    = simplify(evaluated)

    except NotImplementedError as exc:
        return _error(f"Cannot evaluate (no closed form): {_short(exc)}")
    except (TypeError, AttributeError, ValueError) as exc:
        return _error(f"Evaluation error: {_short(exc)}")
    except Exception as exc:
        return _error(f"Unexpected error: {_short(exc)}")
        
    # ── Steps ─────────────────────────────────────────────────────────────────
    stepsMode = settings.get('stepsMode', 'off')
    steps_list = []
    if stepsMode in ('raw', 'friendly'):
        try:
            steps_list = _generate_steps(expr, stepsMode)
        except Exception:
            pass

    # ── Serialise ─────────────────────────────────────────────────────────────
    try:
        result_latex = to_latex(result)
    except Exception as exc:
        return _error(f"Serialisation error: {_short(exc)}")"""
content = content.replace(eval_old, eval_new)

payload_old = """    payload: dict = {"status": "success", "result": result_latex}
    if approx_latex is not None:
        payload["approx"] = approx_latex
    return json.dumps(payload)"""
payload_new = """    payload: dict = {"status": "success", "result": result_latex}
    if approx_latex is not None:
        payload["approx"] = approx_latex
    if steps_list:
        payload["steps"] = steps_list
    return json.dumps(payload)"""
content = content.replace(payload_old, payload_new)


with open("latex_calculator.py", "w") as f:
    f.write(content)

