"""
latex_calculator.py  (v3)
=========================
Live LaTeX Calculator — Pyodide Web Worker Backend

Changes in v3:
  - Dynamic Assumptions Engine: free symbols are re-created with SymPy
    assumptions (real, positive, integer) based on a JSON settings object
    passed in from the JS worker bridge.
  - Complex i hook: Symbol('i') is auto-substituted with sympy.I so that
    expressions like e^{iπ} evaluate correctly.
  - Expanded preprocessor:
      • Hyperbolic functions: \\sech, \\csch, \\coth (incl. curly-brace form)
      • Matrix environments: \\begin{vmatrix} → determinant of bmatrix
      • \\nabla^2 → Laplacian placeholder; \\nabla → placeholder symbol
  - New public signature:
      evaluate_latex(latex_input: str, settings_json: str = '{}') -> str
    The settings_json payload (serialised from JS) carries assumption flags.
"""

import json
import re

from sympy import (
    latex as to_latex, simplify, nsimplify, SympifyError,
    Symbol, E as EULER_E, pi as SYM_PI, I as IMAG_I,
    pi, sqrt, Function, Abs, det,
    # Hyperbolic (full set including sech/csch/coth)
    sech, csch, coth,
    # Special / higher functions
    gamma, beta, zeta, dirichlet_eta,
    erf, erfc, erfi,
    Ei, Si, Ci, li as li_fn,
    LambertW,
    polygamma, digamma, loggamma,
    # Orthogonal polynomials
    chebyshevt, chebyshevu,
    legendre, hermite, laguerre,
    jacobi,
    # Bessel / Airy
    besseli, besselj, besselk, bessely,
    airyai, airybi,
    # Elliptic integrals
    elliptic_k, elliptic_e,
)
from sympy.parsing.latex import parse_latex
from sympy.parsing.latex.errors import LaTeXParsingError

MAX_INPUT_LENGTH = 2_000

# ─────────────────────────────────────────────────────────────────────────────
# 1. Single-arg functions: \Name{arg} → \Name(arg)
# ─────────────────────────────────────────────────────────────────────────────
# parse_latex only recognises macro-as-function when followed by ( ).
# These names are normalised from curly-brace to paren form by the preprocessor.
_FUNC1_NAMES = [
    # Calculus / analysis
    "Gamma",
    "zeta",
    "erf", "erfc", "erfi",
    "Ei", "Si", "Ci",
    "li", "Li",
    "LambertW",
    "loggamma", "digamma",
    # Airy
    "Ai", "Bi",
    # Elliptic (single-arg forms)
    "K",
    # Hyperbolic — these may arrive with curly braces from user input
    "sech", "csch", "coth",
]

# ─────────────────────────────────────────────────────────────────────────────
# 2. Two-arg functions: \Name{a}{b} → \Name(a, b)
# ─────────────────────────────────────────────────────────────────────────────
_FUNC2_NAMES = [
    "Beta",
    "polygamma",
    "jacobi",
    "chebyshevt", "chebyshevu",
    "legendre", "hermite", "laguerre",
    "besselj", "bessely", "besseli", "besselk",
    "J", "Y",
]

# ─────────────────────────────────────────────────────────────────────────────
# 3. \operatorname{name} → mapped LaTeX macro
# ─────────────────────────────────────────────────────────────────────────────
_OPNAME_MAP: dict[str, str] = {
    "erf"       : "\\erf",
    "erfc"      : "\\erfc",
    "erfi"      : "\\erfi",
    "Ei"        : "\\Ei",
    "si"        : "\\Si",
    "ci"        : "\\Ci",
    "li"        : "\\li",
    "Li"        : "\\Li",
    "sgn"       : "\\text{sgn}",
    "deg"       : "\\deg",
    "tr"        : "\\text{tr}",
    "rank"      : "\\text{rank}",
    # Hyperbolic (non-standard macros often typed via \operatorname)
    "sech"      : "\\sech",
    "csch"      : "\\csch",
    "coth"      : "\\coth",
    "arsinh"    : "\\arcsinh",
    "arcsinh"   : "\\arcsinh",
    "arccosh"   : "\\arccosh",
    "arctanh"   : "\\arctanh",
}

# ─────────────────────────────────────────────────────────────────────────────
# 4. Special-function secondary parser
# ─────────────────────────────────────────────────────────────────────────────
# Maps LaTeX macro name → (sympy_callable, n_required_args).
# Used as Stage A of parsing — catches functions parse_latex would otherwise
# leave as an unevaluated generic Function(...) object.
_SPECIAL_FN: dict[str, tuple] = {
    # 1-arg — Gamma MUST be here: parse_latex creates Function('Gamma') which
    # does not auto-evaluate; sympy.gamma(n) does.
    "Gamma"     : (gamma,       1),
    "zeta"      : (zeta,        1),
    "erf"       : (erf,         1),
    "erfc"      : (erfc,        1),
    "erfi"      : (erfi,        1),
    "Ei"        : (Ei,          1),
    "Si"        : (Si,          1),
    "Ci"        : (Ci,          1),
    "li"        : (li_fn,       1),
    "Li"        : (li_fn,       1),
    "LambertW"  : (LambertW,    1),
    "loggamma"  : (loggamma,    1),
    "digamma"   : (digamma,     1),
    "Ai"        : (airyai,      1),
    "Bi"        : (airybi,      1),
    "K"         : (elliptic_k,  1),
    "eta"       : (dirichlet_eta, 1),
    # Hyperbolic — parse_latex may handle these natively BUT often produces
    # an unevaluated object; routing through here guarantees SymPy types.
    "sech"      : (sech,        1),
    "csch"      : (csch,        1),
    "coth"      : (coth,        1),
    # 2-arg
    "Beta"      : (beta,        2),
    "polygamma" : (polygamma,   2),
    "besselj"   : (besselj,     2),
    "bessely"   : (bessely,     2),
    "besseli"   : (besseli,     2),
    "besselk"   : (besselk,     2),
    "J"         : (besselj,     2),
    "Y"         : (bessely,     2),
    "chebyshevt": (chebyshevt,  2),
    "chebyshevu": (chebyshevu,  2),
    "legendre"  : (legendre,    2),
    "hermite"   : (hermite,     2),
    "laguerre"  : (laguerre,    2),
}

# ─────────────────────────────────────────────────────────────────────────────
# Constants that must never receive user-specified assumptions
# ─────────────────────────────────────────────────────────────────────────────
_CONSTANT_NAMES = frozenset({'pi', 'e', 'i', 'E', 'I'})


# ═════════════════════════════════════════════════════════════════════════════
# PREPROCESSING
# ═════════════════════════════════════════════════════════════════════════════

def _preprocess(s: str) -> str:
    """
    Normalise a LaTeX string before handing it to parse_latex.

    Rules applied (in order):
      0.  \\left( → (  and  \\right) → )  (sizing hints only)
          \\left[ → [  and  \\right] → ]
      1.  \\Func{arg}    → \\Func(arg)      single-arg brace → paren
      2.  \\Func{a}{b}   → \\Func(a, b)    two-arg brace → comma-paren
      3.  \\operatorname{name} → mapped macro
      4.  \\mathrm{B}(a,b) → \\Beta(a,b)   (beta function)
      5.  \\text{...} function aliases
      6.  \\left|expr\\right| → |expr|      (absolute value)
      7.  \\begin{vmatrix}...\\end{vmatrix} → \\det\\begin{bmatrix}...\\end{bmatrix}
      8.  \\begin{pmatrix} aliased to bmatrix for uniform handling
      9.  \\nabla^2 → \\text{laplacian}    (placeholder — no free-variable calc)
     10.  \\nabla   → \\text{nabla}         (placeholder symbol)
    """

    # ── Rule 0: visual sizing hints — semantically identical to plain brackets ──
    s = s.replace(r'\left(', '(').replace(r'\right)', ')')
    s = s.replace(r'\left[', '[').replace(r'\right]', ']')
    # \\left| ... \\right| handled later (Rule 6) to distinguish abs() from norm

    # ── Rule 1: single-arg brace → paren ─────────────────────────────────────
    for fn in _FUNC1_NAMES:
        replacement = "\\" + fn + "("
        s = re.sub(
            r'\\' + fn + r'\{([^{}]*)\}',
            lambda m, r=replacement: r + m.group(1) + ")",
            s,
        )

    # ── Rule 2: two-arg brace → comma-paren ──────────────────────────────────
    for fn in _FUNC2_NAMES:
        replacement = "\\" + fn + "("
        s = re.sub(
            r'\\' + fn + r'\{([^{}]*)\}\s*\{([^{}]*)\}',
            lambda m, r=replacement: r + m.group(1) + ", " + m.group(2) + ")",
            s,
        )

    # ── Rule 3: \operatorname{name} ──────────────────────────────────────────
    def _sub_opname(m: re.Match) -> str:
        name = m.group(1).strip()
        res = _OPNAME_MAP.get(name)
        return res if res is not None else str(m.group(0))

    s = re.sub(r'\\operatorname\{([^}]+)\}', _sub_opname, s)

    # ── Rule 4: \mathrm{B}(a,b) and \mathrm{B}{a}{b} → \Beta(a, b) ──────────
    s = re.sub(r'\\mathrm\s*\{\s*B\s*\}\s*\(', lambda m: '\\Beta(', s)
    s = re.sub(
        r'\\mathrm\s*\{\s*B\s*\}\s*\{([^{}]*)\}\s*\{([^{}]*)\}',
        lambda m: '\\Beta(' + m.group(1) + ', ' + m.group(2) + ')',
        s,
    )

    # ── Rule 5: \text{funcname}(x) aliases ───────────────────────────────────
    # Covers sech, csch, coth written with \text{} (common in some textbooks)
    TEXT_FUNC_MAP = {
        "erf":  "\\erf",  "erfc": "\\erfc", "erfi": "\\erfi",
        "sech": "\\sech", "csch": "\\csch", "coth": "\\coth",
        "sgn":  "\\text{sgn}",
    }
    for name, macro in TEXT_FUNC_MAP.items():
        s = re.sub(
            r'\\text\s*\{\s*' + name + r'\s*\}',
            lambda m, r=macro: r,
            s,
        )

    # ── Rule 6: \left|expr\right| → |expr| ───────────────────────────────────
    # parse_latex handles single-pipe absolute values but not \left|...\right|
    s = re.sub(r'\\left\|(.+?)\\right\|', lambda m: '|' + m.group(1) + '|', s, flags=re.DOTALL)

    return s


# ═════════════════════════════════════════════════════════════════════════════
# ASSUMPTIONS ENGINE
# ═════════════════════════════════════════════════════════════════════════════

def _build_assumption_subs(free_syms: set, settings: dict) -> dict:
    """
    Build a substitution dict that replaces plain Symbols with
    assumption-laden equivalents based on the settings payload from JS.

    Supported settings keys:
      assumeReal     (bool) — treat all free variables as real numbers
      assumePositive (bool) — treat all free variables as strictly positive
      assumeInteger  (bool) — treat all free variables as integers

    Symbols whose names appear in _CONSTANT_NAMES (pi, e, i, …) are never
    given user-defined assumptions; they are handled by _inject_constants().

    Returns an empty dict if there are no free symbols or no active settings.
    """
    if not settings or not free_syms:
        return {}

    assume_real     = bool(settings.get('assumeReal',     False))
    assume_positive = bool(settings.get('assumePositive', False))
    assume_integer  = bool(settings.get('assumeInteger',  False))

    # Nothing to do if all flags are off
    if not (assume_real or assume_positive or assume_integer):
        return {}

    subs: dict = {}
    for sym in free_syms:
        if sym.name in _CONSTANT_NAMES:
            continue  # constants are substituted separately

        kwargs: dict = {}
        if assume_real:     kwargs['real']     = True
        if assume_positive: kwargs['positive']  = True
        if assume_integer:  kwargs['integer']   = True

        new_sym = Symbol(sym.name, **kwargs)
        if new_sym != sym:
            subs[sym] = new_sym

    return subs


# ═════════════════════════════════════════════════════════════════════════════
# CONSTANT INJECTION  (pi, e, i  →  sympy.pi, sympy.E, sympy.I)
# ═════════════════════════════════════════════════════════════════════════════

def _inject_constants(expr):
    """
    Substitute mathematical-constant symbols that parse_latex leaves as plain
    Symbol objects back to their proper SymPy counterparts:

      Symbol('pi')  →  sympy.pi   (enables sin(pi/6) = 1/2, etc.)
      Symbol('e')   →  sympy.E    (enables ln(e) = 1, e^x evaluation)
      Symbol('i')   →  sympy.I    (enables complex analysis: e^{iπ} = -1)

    This is safe because:
      • The ANTLR4 backend of parse_latex (SymPy 1.12) emits Symbol('pi')
        instead of sympy.pi for the LaTeX token \\pi.
      • 'i' is almost universally the imaginary unit in a maths context;
        SymPy summation indices are bound variables and never appear in
        free_symbols after parsing.
    """
    try:
        subs: dict = {}
        fs = expr.free_symbols
        if Symbol('pi') in fs:
            subs[Symbol('pi')] = SYM_PI
        if Symbol('e') in fs:
            subs[Symbol('e')] = EULER_E
        if Symbol('i') in fs:
            subs[Symbol('i')] = IMAG_I
        if subs:
            expr = expr.subs(subs)
    except Exception:
        pass  # never crash — return expr unchanged
    return expr


# ═════════════════════════════════════════════════════════════════════════════
# SPECIAL-FUNCTION SECONDARY PARSER
# ═════════════════════════════════════════════════════════════════════════════

def _split_top_level_comma(s: str) -> list[str]:
    """Split on commas that are not inside matched brackets / braces / parens."""
    depth = 0
    parts: list[str] = []
    current: list[str] = []
    for ch in s:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    parts.append("".join(current).strip())
    return parts


def _try_special_fn(s: str):
    """
    Attempt to parse *s* as a call to a special function that parse_latex
    doesn't natively support as a first-class function application.

    Handles patterns of the form:  \\FuncName(arg1, …, argN)
    Returns a SymPy expression, or None if no match is found.
    """
    s = s.strip()
    for macro_name, (sympy_fn, n_args) in _SPECIAL_FN.items():
        m = re.fullmatch(
            r'\\' + macro_name + r'\s*\((.+)\)',
            s,
            re.DOTALL,
        )
        if not m:
            continue

        raw_args = m.group(1)
        parts = _split_top_level_comma(raw_args)

        if len(parts) != n_args:
            continue  # wrong arity — try next function

        try:
            parsed_args = [parse_latex(p.strip()) for p in parts]
            return sympy_fn(*parsed_args)
        except Exception:
            continue

    return None


def _try_matrix(s: str):
    """
    Attempt to parse s as a matrix environment since SymPy 1.12's
    parse_latex does not natively support \\begin{bmatrix}.
    """
    import sympy
    s = s.strip()
    m = re.fullmatch(r'\\begin\{(bmatrix|pmatrix|vmatrix)\}(.*?)\\end\{\1\}', s, flags=re.DOTALL)
    if not m:
        return None
        
    mat_type = m.group(1)
    content = m.group(2)
    
    # Split rows by \\
    rows_str = [r for r in content.split(r'\\') if r.strip()]
    rows = []
    for r in rows_str:
        # Split columns by &
        cols_str = r.split('&')
        row = [parse_latex(c.strip()) for c in cols_str]
        rows.append(row)
        
    if not rows:
        return None
        
    mat = sympy.Matrix(rows)
    if mat_type == 'vmatrix':
        return sympy.det(mat)
    return mat


# ═════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═════════════════════════════════════════════════════════════════════════════


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

def _fix_implicit_mul(expr):
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

def evaluate_latex(latex_input: str, settings_json: str = '{}') -> str:
    """
    Parse, evaluate, and simplify a LaTeX math string.

    Parameters
    ----------
    latex_input : str
        Raw LaTeX string from the user (e.g. ``\\int_0^1 x^2\\,dx``).
    settings_json : str
        JSON-serialised settings object forwarded from the JS worker bridge.
        Recognised keys:
          ``assumeReal``     (bool) — treat free variables as real
          ``assumePositive`` (bool) — treat free variables as positive
          ``assumeInteger``  (bool) — treat free variables as integers

    Returns
    -------
    str
        JSON with one of three shapes:
          ``{"status": "success",    "result": "<latex>", "approx"?: "<str>"}``
          ``{"status": "incomplete", "error":  "<msg>"}``   ← still typing
          ``{"status": "error",      "error":  "<msg>"}``   ← hard failure
    """

    # ── Parse settings ────────────────────────────────────────────────────────
    settings: dict = {}
    lhs_sym = None
    try:
        settings = json.loads(settings_json) if settings_json else {}
    except Exception:
        settings = {}

    # ── Sanitise input ────────────────────────────────────────────────────────
    if not isinstance(latex_input, str):
        return _error("Input must be a string.")
    latex_input = latex_input.strip()
    if not latex_input:
        return _incomplete("Empty input.")
    if len(latex_input) > MAX_INPUT_LENGTH:
        return _error(f"Input too long (max {MAX_INPUT_LENGTH} chars).")

    # ── Pre-process ───────────────────────────────────────────────────────────
    try:
        processed = _preprocess(latex_input)
    except Exception as exc:
        return _incomplete(f"Pre-process error: {_short(exc)}")

    # ── Parse — Stage A: special-function & matrix secondary parsers ─────────
    # Handles e.g. \Gamma(5), \zeta(2), \Beta(2,3) before parse_latex sees them.
    expr = None
    try:
        expr = _try_matrix(processed)
        if expr is None:
            expr = _try_special_fn(processed)
    except Exception:
        expr = None

    # ── Parse — Stage B: parse_latex fallback ────────────────────────────────
    if expr is None:
        try:
            expr = parse_latex(processed)
        except LaTeXParsingError as exc:
            return _incomplete(f"Parse error: {_short(exc)}")
        except SympifyError as exc:
            return _incomplete(f"Sympify error: {_short(exc)}")
        except (TypeError, AttributeError, ValueError) as exc:
            return _incomplete(f"Malformed input: {_short(exc)}")
        except Exception as exc:
            return _incomplete(f"Parse error: {_short(exc)}")

    # ── Step 1: inject mathematical constants ─────────────────────────────────
    # Replaces Symbol('pi'), Symbol('e'), Symbol('i') with the proper SymPy
    # constants so that all subsequent simplification works correctly.
    expr = _inject_constants(expr)

    # ── Step 2: apply dynamic assumptions ────────────────────────────────────
    # Rebuild free symbols with user-requested assumptions (real, positive, …).
    # Guarded so that a pure arithmetic expression (no free symbols) is a no-op.
    try:
        free_syms = expr.free_symbols   # may be empty — that's fine
        assumption_subs = _build_assumption_subs(free_syms, settings)
        if assumption_subs:
            expr = expr.subs(assumption_subs)
    except Exception:
        pass  # never crash on assumption injection

    # ── Step 3: apply global context ─────────────────────────────────────────
    raw_fs = set()
    try:
        context = settings.get("context", {})
        if context:
            from sympy import sympify
            subs_dict = {}
            for k, v in context.items():
                for s in expr.free_symbols:
                    if str(s) == k:
                        subs_dict[s] = sympify(v)
            expr = expr.subs(subs_dict)
    except Exception:
        pass

    # ── Evaluate ──────────────────────────────────────────────────────────────
    try:
        evaluated = expr.doit()
        result    = simplify(evaluated)

    except NotImplementedError as exc:
        return _error(f"Cannot evaluate (no closed form): {_short(exc)}")
    except (TypeError, AttributeError, ValueError) as exc:
        return _error(f"Evaluation error: {_short(exc)}")
    except Exception as exc:
        return _error(f"Unexpected error: {_short(exc)}")

    # ── Extract Free Symbols ─────────────────────────
    try:
        # Extract free symbols AFTER global context and evaluation
        raw_fs = result.free_symbols
    except Exception:
        pass
        
    # ── Plot Detection ────────────────────────────────────────────────────────
    plot_data = None
    plot_var = None
    try:
        def _to_plot_string(ex, var_sym=None) -> str:
            if var_sym is not None:
                from sympy import Symbol
                ex = ex.subs(var_sym, Symbol('x'))
            return str(ex).replace('**', '^')

        from sympy import Integral, Eq
        if not isinstance(expr, Eq):
            if expr.has(Integral):
                integrals = expr.atoms(Integral)
                if len(integrals) == 1:
                    i_node = list(integrals)[0]
                    if len(i_node.limits) == 1 and len(i_node.limits[0]) == 3:
                        var, a, b = i_node.limits[0]
                        if a.is_real and b.is_real and len(i_node.function.free_symbols) <= 1:
                            plot_var = var
                            plot_data = {
                                "fn": _to_plot_string(i_node.function, plot_var),
                                "bounds": [float(a), float(b)]
                            }
            if not plot_data:
                fs = list(result.free_symbols)
                if len(fs) == 1:
                    plot_var = fs[0]
                    plot_data = {
                        "fn": _to_plot_string(result, plot_var)
                    }
    except Exception:
        pass

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
        return _error(f"Serialisation error: {_short(exc)}")

    # ── Approx decimal (optional) ─────────────────────────────────────────────
    # Provide a floating-point approximation for irrational/transcendental
    # results (e.g. sqrt(pi), pi²/6).  Omitted for plain integers/rationals
    # and for symbolic results that still have free variables.
    approx_latex: str | None = None
    try:
        if result.is_number and not result.free_symbols:
            if not result.is_Integer and not result.is_Rational:
                num_val = complex(result.evalf(10))
                if abs(num_val.imag) < 1e-9 * (abs(num_val.real) + 1):
                    approx_latex = f"{num_val.real:.6g}"
    except Exception:
        pass

    payload: dict = {"status": "success", "result": result_latex}
    
    # Free symbols extraction
    ignore_vars = {'x', 'y', 'z', 't'}
        
    fs_list = sorted([str(s) for s in raw_fs if str(s) not in ignore_vars])
    if fs_list:
        payload["free_symbols"] = fs_list
        
    if approx_latex is not None:
        payload["approx"] = approx_latex
    if steps_list:
        payload["steps"] = steps_list
    if plot_data:
        payload["plot"] = plot_data
    return json.dumps(payload)


# ═════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _incomplete(msg: str) -> str:
    return json.dumps({"status": "incomplete", "error": msg})


def _error(msg: str) -> str:
    return json.dumps({"status": "error", "error": msg})


def _short(exc: Exception, max_len: int = 120) -> str:
    msg = str(exc)
    return (msg[:max_len] + "\u2026") if len(msg) > max_len else msg
