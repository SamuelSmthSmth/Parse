import sys

with open("latex_calculator.py", "r") as f:
    content = f.read()

old_raw = """    if mode == 'raw':
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
            pass"""

new_raw = """    if mode == 'raw':
        steps.append(to_latex(expr))
        try:
            expanded = expr.expand()
            if expanded != expr:
                steps.append(to_latex(expanded))
        except Exception:
            pass
        try:
            evaluated = expr.doit()
            if evaluated != expr and (len(steps) == 0 or to_latex(evaluated) != steps[-1]):
                steps.append(to_latex(evaluated))
        except Exception:
            pass
        try:
            simplified = simplify(expr.doit())
            # Make sure we don't duplicate
            if len(steps) == 0 or to_latex(simplified) != steps[-1]:
                if simplified != expr:
                    steps.append(to_latex(simplified))
        except Exception:
            pass"""

if old_raw in content:
    content = content.replace(old_raw, new_raw)
    with open("latex_calculator.py", "w") as f:
        f.write(content)
        print("Patched raw mode successfully.")
else:
    print("Could not find old_raw.")
