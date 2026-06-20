import sys

with open("latex_calculator.py", "r") as f:
    content = f.read()

old_parse = """    try:
        expr = parse_latex(latex_input)
        expr = _fix_implicit_mul(expr)
    except Exception as exc:"""

new_parse = """    is_assignment = False
    lhs_sym = None
    try:
        expr = parse_latex(latex_input)
        expr = _fix_implicit_mul(expr)
        
        # Context Injection
        context = settings.get("context", {})
        subs_dict = {}
        if context:
            from sympy import Symbol, sympify
            for k, v in context.items():
                subs_dict[Symbol(k)] = sympify(v)

        from sympy import Eq, Symbol
        if isinstance(expr, Eq) and isinstance(expr.lhs, Symbol):
            is_assignment = True
            lhs_sym = expr.lhs
            new_rhs = expr.rhs.subs(subs_dict)
            expr = Eq(lhs_sym, new_rhs)
        else:
            expr = expr.subs(subs_dict)
            
    except Exception as exc:"""

content = content.replace(old_parse, new_parse)

old_payload = """    payload: dict = {"status": "success", "result": result_latex}
    if approx_latex is not None:"""

new_payload = """    payload: dict = {"status": "success", "result": result_latex}
    
    if is_assignment:
        from sympy import Eq
        payload["new_assignment"] = {
            "key": str(lhs_sym),
            "val": str(result.rhs) if isinstance(result, Eq) else str(result)
        }
        
    # Free symbols extraction
    ignore_vars = {'x', 'y', 'z', 't'}
    from sympy import Eq
    if isinstance(result, Eq):
        fs = result.rhs.free_symbols
    else:
        fs = result.free_symbols
        
    fs_list = sorted([str(s) for s in fs if str(s) not in ignore_vars])
    if fs_list:
        payload["free_symbols"] = fs_list
        
    if approx_latex is not None:"""

content = content.replace(old_payload, new_payload)

with open("latex_calculator.py", "w") as f:
    f.write(content)

print("Patched python backend for global state successfully.")
