"""
latex_calculator.py  (v2)
=========================
Live LaTeX Calculator — Pyodide Web Worker Backend

Changes in v2:
  - Comprehensive preprocessing: \Func{arg} → \Func(arg)
  - Two-arg preprocessing: \Func{a}{b} → \Func(a, b)
  - \operatorname{...} alias resolution
  - Secondary special-function parser for functions parse_latex
    can't handle as first-class function calls:
    zeta, erf, erfc, erfi, Beta, Ei, Si, Ci, li, LambertW,
    polygamma, digamma, loggamma, chebyshevt, chebyshevu,
    legendre, hermite, laguerre, jacobi, besseli, besselj,
    besselk, bessely, airyai, airybi, dirichlet_eta,
    elliptic_k, elliptic_e
"""

import json
import re

from sympy import (
    latex as to_latex, simplify, nsimplify, SympifyError,
    Symbol, E as EULER_E, pi as SYM_PI,
    pi, sqrt, Function,
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

# ── 1. Single-arg functions: \Name{arg} → \Name(arg) ─────────────────────────
# parse_latex only recognises macro-as-function when followed by ( ).
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
    "K", "E",
]

# ── 2. Two-arg functions: \Name{a}{b} → \Name(a, b) ──────────────────────────
_FUNC2_NAMES = [
    "Beta",             # Beta(a, b) = Γ(a)Γ(b)/Γ(a+b)
    "polygamma",        # polygamma(n, z)
    "jacobi",           # jacobi(n, a, b, x) — handled separately
    "chebyshevt",       # T_n(x)
    "chebyshevu",       # U_n(x)
    "legendre",         # P_n(x)
    "hermite",          # H_n(x)
    "laguerre",         # L_n(x)
    "besselj", "bessely", "besseli", "besselk",  # J_ν(z)
    "J", "Y",
]

# ── 3. \operatorname{name} → mapped LaTeX macro ────────────────────────────────
# Keys are the operatorname text; values are verbatim LaTeX replacement strings.
# IMPORTANT: these are stored as plain strings (not regex patterns), and are
# returned via a lambda in re.sub to avoid \e / \G etc. being treated as
# regex backreferences.
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
    "sech"      : "\\text{sech}",
    "csch"      : "\\text{csch}",
    "arsinh"    : "\\text{arcsinh}",
    "arcsinh"   : "\\text{arcsinh}",
    "arccosh"   : "\\text{arccosh}",
    "arctanh"   : "\\text{arctanh}",
}

# ── 4. Special-function secondary parser ─────────────────────────────────────
#    Maps LaTeX macro name → (sympy_callable, n_required_args)
#    Used when parse_latex can't recognise the macro as a function call.
_SPECIAL_FN: dict[str, tuple] = {
    # 1-arg — NOTE: Gamma MUST be here so we use sympy.gamma (which auto-evaluates)
    # instead of parse_latex's generic Function('Gamma') which does not.
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
    "K"         : (elliptic_k,  1),   # Complete elliptic K(k)
    "eta"       : (dirichlet_eta, 1), # Dirichlet eta η(s)
    # 2-arg
    "Beta"      : (beta,        2),
    "polygamma" : (polygamma,   2),
    "besselj"   : (besselj,     2),
    "bessely"   : (bessely,     2),
    "besseli"   : (besseli,     2),
    "besselk"   : (besselk,     2),
    "J"         : (besselj,     2),   # \J{ν}{z} → besselj(ν, z)
    "Y"         : (bessely,     2),
    "chebyshevt": (chebyshevt,  2),
    "chebyshevu": (chebyshevu,  2),
    "legendre"  : (legendre,    2),
    "hermite"   : (hermite,     2),
    "laguerre"  : (laguerre,    2),
}


# ═════════════════════════════════════════════════════════════════════════════
# PREPROCESSING
# ═════════════════════════════════════════════════════════════════════════════

def _preprocess(s: str) -> str:
    """
    Normalise a LaTeX string before handing it to parse_latex.

    Rules applied (in order):
      0. \\left( → ( and \\right) → )  (sizing hints, not semantic)
      1. \\Func{arg}    → \\Func(arg)      for single-arg special functions
      2. \\Func{a}{b}   → \\Func(a, b)    for two-arg special functions
      3. \\operatorname{name} → mapped macro
      4. \\mathrm{B}(a,b) → \\Beta(a,b)   (beta function)
      5. \\text{...} function aliases
      6. \\left|expr\\right| → |expr|      (absolute value)
    """

    # ── Rule 0: \left(·) and \left[·] are just visual sizing hints ────────────
    # They are ALWAYS semantically identical to ( ) and [ ].  Stripping them
    # early lets _try_special_fn match \Func(arg) even when the user writes
    # \Func\left(arg\right).
    s = s.replace(r'\left(', '(').replace(r'\right)', ')')
    s = s.replace(r'\left[', '[').replace(r'\right]', ']')
    # Leave \left| ... \right| for Rule 6 (absolute value handling)
    for fn in _FUNC1_NAMES:
        # Use a lambda so the replacement string (which contains a backslash)
        # is never parsed as a regex backreference.
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
        return _OPNAME_MAP.get(name, m.group(0))

    s = re.sub(r'\\operatorname\{([^}]+)\}', _sub_opname, s)

    # ── Rule 4: \mathrm{B}(a,b) and \mathrm{B}{a}{b} → \Beta(a, b) ──────────
    s = re.sub(r'\\mathrm\s*\{\s*B\s*\}\s*\(', lambda m: '\\Beta(', s)
    s = re.sub(
        r'\\mathrm\s*\{\s*B\s*\}\s*\{([^{}]*)\}\s*\{([^{}]*)\}',
        lambda m: '\\Beta(' + m.group(1) + ', ' + m.group(2) + ')',
        s,
    )

    # ── Rule 5: \text{erf}(x) etc. ───────────────────────────────────────────
    TEXT_FUNC_MAP = {
        "erf":  "\\erf",  "erfc": "\\erfc", "erfi": "\\erfi",
        "sgn":  "\\text{sgn}",
        "sech": "\\text{sech}", "csch": "\\text{csch}",
    }
    for name, macro in TEXT_FUNC_MAP.items():
        s = re.sub(
            r'\\text\s*\{\s*' + name + r'\s*\}',
            lambda m, r=macro: r,
            s,
        )

    # ── Rule 6: \left|expr\right| → |expr| (parse_latex handles single pipes) ──
    s = re.sub(r'\\left\|(.+?)\\right\|', lambda m: '|' + m.group(1) + '|', s, flags=re.DOTALL)

    return s


# ═════════════════════════════════════════════════════════════════════════════
# SPECIAL-FUNCTION SECONDARY PARSER
# ═════════════════════════════════════════════════════════════════════════════

def _split_top_level_comma(s: str) -> list[str]:
    """Split string on commas that are not inside brackets/braces/parens."""
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
    Attempt to parse s as a call to one of the special functions that
    parse_latex doesn't natively support as function application.

    Returns a SymPy expression or None.
    Only handles patterns of the form: \\FuncName(arg1, ..., argN)
    """
    s = s.strip()
    for macro_name, (sympy_fn, n_args) in _SPECIAL_FN.items():
        # Build a regex that matches \MacroName(...)
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
            continue  # wrong arity

        try:
            parsed_args = [parse_latex(p.strip()) for p in parts]
            return sympy_fn(*parsed_args)
        except Exception:
            continue  # try next match

    return None


# ═════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═════════════════════════════════════════════════════════════════════════════

def evaluate_latex(latex_input: str) -> str:
    """
    Parse, evaluate, and simplify a LaTeX math string.

    Returns a JSON string with one of three shapes:
      {"status": "success",    "result": "<latex>"}
      {"status": "incomplete", "error":  "<msg>"}   ← user still typing
      {"status": "error",      "error":  "<msg>"}   ← hard failure
    """

    # ── Sanitise ──────────────────────────────────────────────────────────────
    if not isinstance(latex_input, str):
        return _error("Input must be a string.")
    latex_input = latex_input.strip()
    if not latex_input:
        return _incomplete("Empty input.")
    if len(latex_input) > MAX_INPUT_LENGTH:
        return _error(f"Input too long (max {MAX_INPUT_LENGTH} chars).")

    # ── Pre-process ────────────────────────────────────────────────────────────
    try:
        processed = _preprocess(latex_input)
    except Exception as exc:
        return _incomplete(f"Pre-process error: {_short(exc)}")

    # ── Parse (two-stage) ──────────────────────────────────────────────────────
    expr = None

    # Stage A: try the special-function secondary parser first on the full
    # expression (handles simple cases like \zeta(2), \Beta(1,2) etc.)
    try:
        expr = _try_special_fn(processed)
    except Exception:
        expr = None

    # Stage B: fall back to parse_latex
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

    # ── Post-parse: substitute math constants parse_latex leaves as Symbols ──
    # parse_latex (ANTLR4 backend, SymPy 1.12) creates Symbol('pi') and
    # Symbol('e') instead of sympy.pi / sympy.E.  Substituting them here lets
    # SymPy auto-evaluate: sin(pi/6)→1/2, cos(pi)→-1, ln(e)→1, etc.
    try:
        subs = {}
        fs = expr.free_symbols
        if Symbol('pi') in fs:
            subs[Symbol('pi')] = SYM_PI
        if Symbol('e') in fs:
            subs[Symbol('e')] = EULER_E
        if subs:
            expr = expr.subs(subs)
    except Exception:
        pass

    # ── Evaluate ───────────────────────────────────────────────────────────────
    try:
        evaluated = expr.doit()
        result    = simplify(evaluated)
        # _force_eval uses nsimplify(evalf()) to handle any remaining
        # unevaluated function calls that survive simplify (e.g. asin(1/2)
        # built with evaluate=False by parse_latex).
        # Guard: only fire when result is numeric AND still contains a
        # Function atom.  This avoids corrupting already-exact expressions
        # like sqrt(pi) or pi**2/6 with rational approximations.
        if result.is_number and not result.is_Number and result.atoms(Function):
            result = _force_eval(result)
    except NotImplementedError as exc:
        return _error(f"Cannot evaluate (no closed form): {_short(exc)}")
    except (TypeError, AttributeError, ValueError) as exc:
        return _error(f"Evaluation error: {_short(exc)}")
    except Exception as exc:
        return _error(f"Unexpected error: {_short(exc)}")

    # ── Serialise ──────────────────────────────────────────────────────────────
    try:
        result_latex = to_latex(result)
    except Exception as exc:
        return _error(f"Serialisation error: {_short(exc)}")

    return json.dumps({"status": "success", "result": result_latex})


# ─── Helpers ──────────────────────────────────────────────────────────────────

# Known exact constants for nsimplify to search over
_NSIMPLIFY_CONSTANTS = [pi, EULER_E, sqrt(2), sqrt(3), sqrt(5), sqrt(6), sqrt(7)]

def _force_eval(expr):
    """
    For fully numeric expressions (no free symbols) that parse_latex built
    with evaluate=False internally, use evalf() → nsimplify() to obtain the
    exact algebraic form.

    Examples:
      sin(pi/6)  → 1/2
      cos(pi)    → -1
      ln(E)      → 1
      gamma(5)   → 24  (already evaluated via _SPECIAL_FN, but as safety net)
    """
    try:
        numerical = complex(expr.evalf(25))
        if abs(numerical.imag) > 1e-9 * (abs(numerical.real) + 1):
            return expr  # genuinely complex — don't force to real
        val = float(numerical.real)
        nice = nsimplify(val, _NSIMPLIFY_CONSTANTS, rational=True, tolerance=1e-10)
        # Sanity: only accept if the "nice" form agrees to 8 significant figures
        if abs(complex(nice.evalf(10)).real - val) < 1e-7 * (abs(val) + 1):
            return nice
    except Exception:
        pass
    return expr


def _incomplete(msg: str) -> str:
    return json.dumps({"status": "incomplete", "error": msg})

def _error(msg: str) -> str:
    return json.dumps({"status": "error", "error": msg})

def _short(exc: Exception, max_len: int = 120) -> str:
    msg = str(exc)
    return (msg[:max_len] + "\u2026") if len(msg) > max_len else msg
