import sys

with open("latex_calculator.py", "r") as f:
    content = f.read()

func = """def _fix_implicit_mul(expr):
    from sympy.core.function import AppliedUndef
    from sympy import Symbol
    if isinstance(expr, AppliedUndef):
        func_name = expr.func.__name__
        if func_name in ('i', 'j', 'k', 'n', 'm', 'x', 'y', 'z', 'a', 'b', 'c', 't', 'u', 'v', 'w'):
            if len(expr.args) == 1:
                return Symbol(func_name) * _fix_implicit_mul(expr.args[0])
    if expr.args:
        return expr.func(*[_fix_implicit_mul(a) for a in expr.args])
    return expr

def evaluate_latex(latex_input: str, settings_json: str = '{}') -> str:"""

content = content.replace("def evaluate_latex(latex_input: str, settings_json: str = '{}') -> str:", func)

old_parse = """    try:
        expr = parse_latex(latex_input)
    except Exception as exc:
        # Some errors from antlr4 are raw Exceptions, others are LaTeXParsingError"""

new_parse = """    try:
        expr = parse_latex(latex_input)
        expr = _fix_implicit_mul(expr)
    except Exception as exc:
        # Some errors from antlr4 are raw Exceptions, others are LaTeXParsingError"""

content = content.replace(old_parse, new_parse)

with open("latex_calculator.py", "w") as f:
    f.write(content)
    print("Patched implicit mul successfully.")

